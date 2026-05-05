"""
approve_content.py  –  drafts/{id}/ を approved/{id}/ に移す
=============================================================
使い方:
    python scripts/approve_content.py --id 2026-05-05_001
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.utils import get_logger, update_status, get_status

log = get_logger("approve_content")


def approve(item_id: str) -> bool:
    src = Path("drafts") / item_id
    dst = Path("approved") / item_id

    if not src.exists():
        log.error("drafts/%s が見つかりません", item_id)
        return False

    status = get_status(src)
    if status not in {"draft", "needs_fix"}:
        log.warning("ステータスが '%s' です（draft / needs_fix 以外は非推奨）", status)

    if dst.exists():
        log.warning("approved/%s はすでに存在します。上書きします", item_id)
        shutil.rmtree(dst)

    shutil.copytree(str(src), str(dst))
    update_status(dst, "approved")
    log.info("✅ 承認完了: approved/%s/", item_id)
    log.info("   次のステップ: python scripts/post_to_instagram.py --id %s", item_id)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="下書きを承認済みに移します")
    parser.add_argument("--id", required=True, help="承認するアイデアID")
    return 0 if approve(parser.parse_args().id) else 2


if __name__ == "__main__":
    sys.exit(main())
