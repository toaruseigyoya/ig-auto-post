"""
post_to_instagram.py  –  approved/{id}/ を Instagram に投稿する
================================================================
使い方:
    python scripts/post_to_instagram.py              # approved の最古を投稿
    python scripts/post_to_instagram.py --id 2026-05-05_001  # 指定ID
    python scripts/post_to_instagram.py --dry-run    # 動作確認（投稿しない）

フロー:
    1. approved/{id}/ から画像・キャプション読み込み
    2. publish_to_pages.py で GitHub Pages に公開 → image_url 取得
    3. Instagram Graph API で2ステップ投稿
    4. post_result.json 保存
    5. posted/{id}/ に移動
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.utils import (
    get_logger, read_text, write_json, update_status, find_folders_with_status,
)
from scripts.publish_to_pages import publish as publish_image

load_dotenv()
log = get_logger("post_to_instagram")

JST = timezone(timedelta(hours=9))
GRAPH_API_VERSION     = "v21.0"
GRAPH_API_BASE        = f"https://graph.facebook.com/{GRAPH_API_VERSION}"
MAX_STATUS_CHECKS     = 10
STATUS_CHECK_INTERVAL = 3


# ---------------------------------------------------------------------------
# Instagram Graph API
# ---------------------------------------------------------------------------

def create_container(user_id: str, token: str, image_url: str, caption: str) -> str:
    url = f"{GRAPH_API_BASE}/{user_id}/media"
    resp = requests.post(url, data={
        "image_url": image_url,
        "caption": caption,
        "access_token": token,
    }, timeout=30)
    data = _parse(resp, "create_container")
    cid = data.get("id")
    if not cid:
        raise RuntimeError(f"creation_id 取得失敗: {data}")
    log.info("  creation_id: %s", cid)
    return cid


def wait_finished(cid: str, token: str) -> None:
    url = f"{GRAPH_API_BASE}/{cid}"
    for attempt in range(1, MAX_STATUS_CHECKS + 1):
        resp = requests.get(url, params={
            "fields": "status_code,status",
            "access_token": token,
        }, timeout=15)
        data = _parse(resp, "wait_finished")
        sc = data.get("status_code")
        log.info("  status: %s (%d/%d)", sc, attempt, MAX_STATUS_CHECKS)
        if sc == "FINISHED":
            return
        if sc in {"ERROR", "EXPIRED"}:
            raise RuntimeError(f"コンテナ失敗: {data}")
        time.sleep(STATUS_CHECK_INTERVAL)
    raise TimeoutError("FINISHED にならなかった")


def publish_post(user_id: str, token: str, cid: str) -> str:
    url = f"{GRAPH_API_BASE}/{user_id}/media_publish"
    resp = requests.post(url, data={
        "creation_id": cid,
        "access_token": token,
    }, timeout=30)
    data = _parse(resp, "publish_post")
    mid = data.get("id")
    if not mid:
        raise RuntimeError(f"media_id 取得失敗: {data}")
    log.info("  media_id: %s", mid)
    return mid


def _parse(resp: requests.Response, label: str) -> dict:
    try:
        data = resp.json()
    except Exception:
        raise RuntimeError(f"[{label}] JSON parse error: {resp.text[:300]}")
    if resp.status_code >= 400 or "error" in data:
        err = data.get("error", {})
        raise RuntimeError(
            f"[{label}] APIエラー code={err.get('code')} "
            f"message={err.get('message')} | {data}"
        )
    return data


# ---------------------------------------------------------------------------
# メイン
# ---------------------------------------------------------------------------

def post_item(item_id: str, dry_run: bool = False) -> bool:
    approved_folder = Path("approved") / item_id
    if not approved_folder.exists():
        log.error("approved/%s が見つかりません", item_id)
        return False

    # キャプション読み込み
    cap_path = approved_folder / "caption.txt"
    caption = read_text(cap_path) if cap_path.exists() else "#4コマ漫画 #日常"
    log.info("キャプション: %s", caption[:60])

    if dry_run:
        log.info("【DRY RUN】実際には投稿しません")
        log.info("  対象: approved/%s", item_id)
        return True

    # 環境変数
    token   = os.getenv("IG_ACCESS_TOKEN", "")
    user_id = os.getenv("IG_USER_ID", "")
    if not token or not user_id:
        log.error(".env に IG_ACCESS_TOKEN / IG_USER_ID が設定されていません")
        return False

    update_status(approved_folder, "posting")

    try:
        # 1. GitHub Pages に公開
        log.info("GitHub Pages に公開中...")
        image_url = publish_image(item_id)
        if not image_url:
            raise RuntimeError("image_url の取得失敗")

        # 2. Instagram 投稿
        log.info("Instagram に投稿中...")
        cid = create_container(user_id, token, image_url, caption)
        wait_finished(cid, token)
        mid = publish_post(user_id, token, cid)

        # 3. 結果保存
        result = {
            "id": item_id,
            "posted_at": datetime.now(JST).isoformat(),
            "instagram_creation_id": cid,
            "instagram_media_id": mid,
            "image_url": image_url,
            "status": "posted",
        }
        write_json(approved_folder / "post_result.json", result)

        # 4. posted/ に移動
        posted_folder = Path("posted") / item_id
        posted_folder.parent.mkdir(exist_ok=True)
        if posted_folder.exists():
            shutil.rmtree(posted_folder)
        shutil.move(str(approved_folder), str(posted_folder))
        update_status(posted_folder, "posted")

        log.info("=" * 55)
        log.info("✅ 投稿成功！ media_id = %s", mid)
        log.info("   フォルダ: posted/%s/", item_id)
        log.info("=" * 55)
        return True

    except Exception as e:
        log.error("投稿失敗: %s", e)
        update_status(approved_folder, "error", {"error_message": str(e)})
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="承認済みコンテンツをInstagramに投稿します")
    parser.add_argument("--id", help="投稿するアイデアID（省略時は最古のapprovedを投稿）")
    parser.add_argument("--dry-run", action="store_true", help="テスト実行（実際には投稿しない）")
    args = parser.parse_args()

    if args.id:
        target_id = args.id
    else:
        folders = find_folders_with_status(Path("approved"), "approved")
        if not folders:
            log.warning("approved/ に投稿対象がありません")
            return 0
        target_id = folders[0].name
        log.info("投稿対象: %s", target_id)

    ok = post_item(target_id, dry_run=args.dry_run)
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
