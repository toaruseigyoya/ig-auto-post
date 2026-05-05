"""
generate_content.py  –  ideas/{id}/idea.json → drafts/{id}/ を生成する
=======================================================================
使い方:
    python scripts/generate_content.py              # 未処理ネタを全件処理
    python scripts/generate_content.py --id 2026-05-05_001  # 指定IDのみ

生成物:
    drafts/{id}/image.png      … 4コマ漫画画像（1080x1080）
    drafts/{id}/caption.txt    … Instagramキャプション
    drafts/{id}/prompt.txt     … 生成に使ったプロンプト情報
    drafts/{id}/meta.json      … メタ情報
    drafts/{id}/status.json    … ステータス（draft）
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# PIL がなければ pip install Pillow でインストール
try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("ERROR: Pillow がインストールされていません。")
    print("  pip install Pillow")
    sys.exit(1)

# プロジェクトルートをパス追加
sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.utils import (
    get_logger, read_json, write_json, write_text, update_status,
    find_folders_with_status,
)

log = get_logger("generate_content")

# ---------------------------------------------------------------------------
# 画像設定
# ---------------------------------------------------------------------------

OUTPUT_SIZE  = (1080, 1080)
PANEL_ROWS   = 2
PANEL_COLS   = 2
BORDER       = 4
MARGIN       = 12
BG_COLOR     = (255, 255, 255)
BORDER_COLOR = (30, 30, 30)
TEXT_COLOR   = (20, 20, 20)
LABEL_COLOR  = (130, 130, 130)
PANEL_BG     = (248, 248, 248)
PANEL_LABELS = ["①", "②", "③", "④"]

FONT_CANDIDATES = [
    "C:/Windows/Fonts/meiryo.ttc",
    "C:/Windows/Fonts/YuGothM.ttc",
    "C:/Windows/Fonts/msgothic.ttc",
    "C:/Windows/Fonts/NotoSansCJK-Regular.ttc",
]


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


# ---------------------------------------------------------------------------
# 台本生成（ルールベース）
# ---------------------------------------------------------------------------

def gen_script(idea: dict) -> list[dict]:
    """idea.json の情報から4コマ台本を生成する。"""
    summary  = idea.get("summary", "")
    theme    = idea.get("theme", "")
    tone     = idea.get("tone", "")

    sentences = _split_sentences(summary)

    if len(sentences) >= 4:
        parts = _distribute(sentences, 4)
    elif len(sentences) == 3:
        parts = [sentences[0], sentences[1], sentences[1], sentences[2]]
    elif len(sentences) == 2:
        parts = [sentences[0], sentences[0], sentences[1], sentences[1]]
    else:
        parts = _split_single(sentences[0] if sentences else summary)

    scene_labels = ["日常", "展開", "クライマックス", "オチ"]
    panels = []
    for i, scene in enumerate(scene_labels):
        dialog = parts[i] if i < len(parts) else ""
        panels.append({
            "panel":  i + 1,
            "label":  PANEL_LABELS[i],
            "scene":  scene,
            "dialog": dialog,
            "theme":  theme,
        })
    return panels


def _split_sentences(text: str) -> list[str]:
    raw = re.split(r'[。！？\n\.!?]+', text)
    return [s.strip() for s in raw if s.strip()] or [text.strip()]


def _distribute(sentences: list[str], n: int) -> list[str]:
    if len(sentences) == n:
        return list(sentences)
    result = []
    step = len(sentences) / n
    for i in range(n):
        chunk = sentences[round(i * step): round((i + 1) * step)]
        result.append("。".join(chunk) if chunk else "")
    return result


def _split_single(text: str) -> list[str]:
    n = len(text)
    if n <= 4:
        return [text, text, text, text]
    s = n // 4
    return [text[:s], text[s:s*2], text[s*2:s*3], text[s*3:]]


# ---------------------------------------------------------------------------
# 画像合成
# ---------------------------------------------------------------------------

def compose_image(panels: list[dict], out_path: Path) -> None:
    """4コマ漫画画像を生成して out_path に保存する。"""
    W, H = OUTPUT_SIZE
    img  = Image.new("RGB", (W, H), BG_COLOR)
    draw = ImageDraw.Draw(img)

    inner_w = (W - MARGIN * 2 - BORDER * (PANEL_COLS + 1)) // PANEL_COLS
    inner_h = (H - MARGIN * 2 - BORDER * (PANEL_ROWS + 1)) // PANEL_ROWS

    font_dialog = _load_font(30)
    font_label  = _load_font(22)
    font_scene  = _load_font(18)

    for idx, panel in enumerate(panels):
        row = idx // PANEL_COLS
        col = idx  % PANEL_COLS

        x0 = MARGIN + BORDER + col * (inner_w + BORDER)
        y0 = MARGIN + BORDER + row * (inner_h + BORDER)
        x1 = x0 + inner_w
        y1 = y0 + inner_h

        draw.rectangle([x0, y0, x1, y1], fill=PANEL_BG)
        draw.rectangle([x0 - BORDER, y0 - BORDER, x1 + BORDER, y1 + BORDER],
                       outline=BORDER_COLOR, width=BORDER)

        # コマ番号
        draw.text((x0 + 8, y0 + 6), panel["label"], font=font_label, fill=LABEL_COLOR)

        # シーン名
        draw.text((x0 + 36, y0 + 8), panel["scene"], font=font_scene, fill=LABEL_COLOR)

        # セリフ
        wrapped = _wrap_text(panel["dialog"], font_dialog, inner_w - 20)
        _draw_lines(draw, wrapped, font_dialog, x0 + 10, y0 + inner_h // 3, TEXT_COLOR)

    # 外枠
    draw.rectangle([MARGIN, MARGIN, W - MARGIN, H - MARGIN],
                   outline=BORDER_COLOR, width=BORDER)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(out_path), "PNG")


def _wrap_text(text: str, font: ImageFont.FreeTypeFont, max_w: int) -> list[str]:
    lines, cur = [], ""
    for ch in text:
        test = cur + ch
        bbox = font.getbbox(test)
        if bbox[2] - bbox[0] > max_w and cur:
            lines.append(cur)
            cur = ch
        else:
            cur = test
    if cur:
        lines.append(cur)
    return lines


def _draw_lines(draw, lines, font, x, y, color):
    lh = font.getbbox("あ")[3] + 6
    for i, line in enumerate(lines):
        draw.text((x, y + i * lh), line, font=font, fill=color)


# ---------------------------------------------------------------------------
# キャプション生成
# ---------------------------------------------------------------------------

def gen_caption(idea: dict) -> str:
    summary  = idea.get("summary", "")
    hashtags = idea.get("hashtags", [])
    theme    = idea.get("theme", "")

    lines = [summary, ""]
    if theme:
        lines.append(f"テーマ：{theme}")
        lines.append("")
    lines.append(" ".join(hashtags) if hashtags else "#4コマ漫画 #日常 #あるある")
    return "\n".join(lines)


def gen_prompt_text(idea: dict) -> str:
    return (
        f"テーマ：{idea.get('theme', '')}\n"
        f"形式：{idea.get('category', '4コマ漫画')}\n"
        f"読者：{idea.get('target', '')}\n"
        f"内容：{idea.get('summary', '')}\n"
        f"トーン：{idea.get('tone', '')}\n"
    )


# ---------------------------------------------------------------------------
# 1件処理
# ---------------------------------------------------------------------------

def process_idea(idea_folder: Path) -> bool:
    idea_path = idea_folder / "idea.json"
    if not idea_path.exists():
        log.error("idea.json が見つかりません: %s", idea_path)
        return False

    idea = read_json(idea_path)
    item_id = idea.get("id", idea_folder.name)

    log.info("--- 処理開始: %s ---", item_id)
    update_status(idea_folder, "generating")

    draft_folder = Path("drafts") / item_id
    draft_folder.mkdir(parents=True, exist_ok=True)

    try:
        # 台本生成
        panels = gen_script(idea)
        log.info("  台本生成完了 (%d コマ)", len(panels))

        # 画像生成
        image_path = draft_folder / "image.png"
        compose_image(panels, image_path)
        log.info("  画像生成完了: %s", image_path)

        # キャプション
        caption = gen_caption(idea)
        write_text(draft_folder / "caption.txt", caption)
        log.info("  キャプション生成完了")

        # プロンプトテキスト
        write_text(draft_folder / "prompt.txt", gen_prompt_text(idea))

        # メタ情報
        meta = {
            "id": item_id,
            "theme": idea.get("theme", ""),
            "generated_at": datetime.now().isoformat(),
            "generator": "local",
            "version": 1,
            "status": "draft",
        }
        write_json(draft_folder / "meta.json", meta)

        # idea.json をコピー
        write_json(draft_folder / "idea.json", idea)

        # ステータス更新
        update_status(idea_folder, "draft")
        update_status(draft_folder, "draft")

        log.info("✅ 完了: drafts/%s/", item_id)
        return True

    except Exception as e:
        log.error("生成失敗: %s", e)
        update_status(idea_folder, "error", {"error_message": str(e)})
        update_status(draft_folder, "error", {"error_message": str(e)})
        return False


# ---------------------------------------------------------------------------
# エントリポイント
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="ネタから下書きを生成します")
    parser.add_argument("--id", help="処理するアイデアID（省略時は全件）")
    args = parser.parse_args()

    if args.id:
        folder = Path("ideas") / args.id
        if not folder.exists():
            log.error("ideas/%s が見つかりません", args.id)
            return 1
        ok = process_idea(folder)
        return 0 if ok else 2

    # 全未処理を処理
    target_statuses = {"idea", "unknown"}
    ideas_dir = Path("ideas")
    if not ideas_dir.exists():
        log.warning("ideas/ フォルダがありません")
        return 0

    folders = sorted(
        [d for d in ideas_dir.iterdir()
         if d.is_dir() and (d / "idea.json").exists()],
        key=lambda d: d.name,
    )

    pending = []
    for f in folders:
        status_path = f / "status.json"
        if not status_path.exists():
            pending.append(f)
        else:
            from scripts.utils import get_status
            s = get_status(f)
            if s in target_statuses:
                pending.append(f)

    if not pending:
        log.info("処理対象のネタがありません。")
        return 0

    log.info("処理対象: %d 件", len(pending))
    errors = 0
    for folder in pending:
        if not process_idea(folder):
            errors += 1

    log.info("完了 (成功: %d / 失敗: %d)", len(pending) - errors, errors)
    return 0 if errors == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
