"""
regenerate_content.py  –  修正指示を反映して下書きを再生成する
=================================================================
使い方:
    python scripts/regenerate_content.py --id 2026-05-05_001

前提:
    drafts/{id}/fix_request.txt が存在すること

処理:
    - fix_request.txt の内容を読む
    - 画像・キャプションを再生成する
    - meta.version を +1 する
    - status を draft に戻す
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.utils import (
    get_logger, read_json, write_json, write_text, read_text, update_status,
)
from scripts.generate_content import gen_script, compose_image, gen_caption

log = get_logger("regenerate_content")


def regenerate(item_id: str) -> bool:
    draft_folder = Path("drafts") / item_id
    if not draft_folder.exists():
        log.error("drafts/%s が見つかりません", item_id)
        return False

    fix_path = draft_folder / "fix_request.txt"
    if not fix_path.exists():
        log.warning("fix_request.txt がありません: %s", fix_path)
        log.info("  → そのまま再生成します")
        fix_notes = ""
    else:
        fix_notes = read_text(fix_path)
        log.info("修正指示を読み込みました:")
        for line in fix_notes.splitlines():
            log.info("  > %s", line)

    idea_path = draft_folder / "idea.json"
    if not idea_path.exists():
        log.error("idea.json が見つかりません: %s", idea_path)
        return False

    idea = read_json(idea_path)

    # 修正指示をキャプションに反映（テキスト修正がある場合）
    if fix_notes:
        # キャプションへの指示を簡易検出
        cap_path = draft_folder / "caption.txt"
        if cap_path.exists():
            current_caption = read_text(cap_path)
            log.info("  現在のキャプション:\n%s", current_caption)
        # fix_request.txt の内容を注釈としてプロンプトに追記
        idea["_fix_notes"] = fix_notes

    update_status(draft_folder, "regenerating")

    try:
        # 画像再生成
        panels = gen_script(idea)
        image_path = draft_folder / "image.png"
        compose_image(panels, image_path)
        log.info("  画像再生成完了")

        # キャプション再生成
        caption = gen_caption(idea)
        if fix_notes and "キャプション" in fix_notes:
            # 修正指示にキャプション関連があれば末尾にメモ追記
            caption += f"\n\n【修正メモ】{fix_notes[:100]}"
        write_text(draft_folder / "caption.txt", caption)
        log.info("  キャプション再生成完了")

        # meta.version +1
        meta_path = draft_folder / "meta.json"
        meta = read_json(meta_path) if meta_path.exists() else {}
        meta["version"] = meta.get("version", 1) + 1
        meta["regenerated_at"] = __import__("datetime").datetime.now().isoformat()
        meta["fix_applied"] = bool(fix_notes)
        write_json(meta_path, meta)

        # fix_request.txt を fix_request_applied.txt にリネーム
        if fix_path.exists():
            fix_path.rename(draft_folder / "fix_request_applied.txt")

        update_status(draft_folder, "draft")
        log.info("✅ 再生成完了: drafts/%s/  (version=%d)", item_id, meta["version"])
        return True

    except Exception as e:
        log.error("再生成失敗: %s", e)
        update_status(draft_folder, "error", {"error_message": str(e)})
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="修正指示を反映して下書きを再生成します")
    parser.add_argument("--id", required=True, help="再生成するアイデアID")
    args = parser.parse_args()
    return 0 if regenerate(args.id) else 2


if __name__ == "__main__":
    sys.exit(main())
