"""
add_idea.py  –  投稿ネタを対話式で登録するCLIツール
====================================================
使い方:
    python add_idea.py
    python add_idea.py --auto  # 対話なし（デフォルト値で作成してテスト用）
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from scripts.utils import get_logger, write_json, new_idea_id, update_status

log = get_logger("add_idea")
JST = timezone(timedelta(hours=9))

CATEGORY_OPTIONS = ["4コマ漫画", "1枚イラスト", "Quote"]
TONE_OPTIONS     = ["やさしい・共感系", "笑い・ユーモア", "学び・気づき", "感動・共感"]


def prompt(label: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    val = input(f"{label}{suffix}: ").strip()
    return val if val else default


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--auto", action="store_true", help="テスト用：デフォルト値で自動作成")
    args = parser.parse_args()

    print()
    print("=" * 50)
    print("  📝 ネタ登録")
    print("=" * 50)
    print()

    if args.auto:
        idea_id  = new_idea_id()
        theme    = "日常"
        category = "4コマ漫画"
        target   = "一般"
        summary  = "今日もなんとか一日が終わった。疲れたけど、それでいい。明日もきっと大丈夫。"
        tone     = "やさしい・共感系"
        hashtags = ["#日常", "#4コマ漫画", "#あるある"]
    else:
        idea_id  = new_idea_id()
        print(f"  新しいID: {idea_id}")
        print()
        theme    = prompt("テーマ（例：子育て、仕事、心理学）", "日常")
        category = prompt(f"カテゴリ（{'/'.join(CATEGORY_OPTIONS)}）", "4コマ漫画")
        target   = prompt("想定読者（例：子育て中の親）", "一般")
        summary  = prompt("内容の要約（投稿ネタの文章）")
        if not summary:
            log.error("内容の要約は必須です")
            return 1
        tone     = prompt(f"トーン（{'/'.join(TONE_OPTIONS)}）", "やさしい・共感系")
        tags_raw = prompt("ハッシュタグ（スペース区切り、# は不要）", "4コマ漫画 日常 あるある")
        hashtags = [f"#{t}" for t in tags_raw.split()]

    idea = {
        "id": idea_id,
        "theme": theme,
        "category": category,
        "target": target,
        "summary": summary,
        "tone": tone,
        "post_type": "feed",
        "hashtags": hashtags,
        "created_at": datetime.now(JST).isoformat(),
        "status": "idea",
    }

    # 保存
    folder = Path("ideas") / idea_id
    folder.mkdir(parents=True, exist_ok=True)
    write_json(folder / "idea.json", idea)
    update_status(folder, "idea")

    print()
    print(f"✅ 登録完了！  ideas/{idea_id}/")
    print()
    print("次のステップ:")
    print(f"  python scripts/generate_content.py --id {idea_id}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
