"""
publish_to_pages.py  –  承認済み画像を GitHub Pages に公開する
==============================================================
使い方:
    python scripts/publish_to_pages.py --id 2026-05-05_001

処理:
    1. approved/{id}/image.png を public/images/ig/{id}.png にコピー
    2. git add + commit + push
    3. 公開URLを返す

.env 設定:
    GITHUB_PAGES_BASE_URL  … 例: https://toaruseigyoya.github.io
    GITHUB_PAGES_IMG_DIR   … 例: images/ig  (省略時は images/ig)
    GITHUB_PAGES_REPO_PATH … 別リポジトリの場合はそのパス（省略時はカレントdir）
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.utils import get_logger

load_dotenv()
log = get_logger("publish_to_pages")

PAGES_BASE_URL  = os.getenv("GITHUB_PAGES_BASE_URL", "https://toaruseigyoya.github.io")
PAGES_IMG_DIR   = os.getenv("GITHUB_PAGES_IMG_DIR", "images/ig")
PAGES_REPO_PATH = os.getenv("GITHUB_PAGES_REPO_PATH", ".")


def publish(item_id: str) -> str | None:
    """
    画像を GitHub Pages に公開し、公開URLを返す。
    失敗時は None を返す。
    """
    src = Path("approved") / item_id / "image.png"
    if not src.exists():
        log.error("approved/%s/image.png が見つかりません", item_id)
        return None

    # コピー先
    repo_root = Path(PAGES_REPO_PATH).resolve()
    img_dir   = repo_root / PAGES_IMG_DIR
    img_dir.mkdir(parents=True, exist_ok=True)
    dst = img_dir / f"{item_id}.png"

    shutil.copy2(str(src), str(dst))
    log.info("  コピー完了: %s → %s", src, dst)

    # git push
    try:
        _git(["add", str(dst)], cwd=repo_root)
        _git(["commit", "-m", f"Add image: {item_id}"], cwd=repo_root)
        _git(["push"], cwd=repo_root)
        log.info("  GitHub Pages に push しました")
    except subprocess.CalledProcessError as e:
        log.warning("git push 失敗（ローカルコピーは完了）: %s", e)
        log.warning("  手動で push してから投稿してください")

    # 公開URL
    # base_url にリポジトリ名が含まれていない場合（個人Pages: username.github.io）
    url = f"{PAGES_BASE_URL.rstrip('/')}/{PAGES_IMG_DIR}/{item_id}.png"
    log.info("  公開URL: %s", url)

    # GitHub Pages の反映に少し待つ
    log.info("  GitHub Pages の反映を待っています（10秒）...")
    time.sleep(10)

    return url


def _git(args: list[str], cwd: Path) -> None:
    result = subprocess.run(
        ["git"] + args,
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        # "nothing to commit" は正常
        if "nothing to commit" in result.stdout or "nothing to commit" in result.stderr:
            return
        raise subprocess.CalledProcessError(result.returncode, args, result.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description="承認済み画像を GitHub Pages に公開します")
    parser.add_argument("--id", required=True, help="アイデアID")
    args = parser.parse_args()
    url = publish(args.id)
    return 0 if url else 2


if __name__ == "__main__":
    sys.exit(main())
