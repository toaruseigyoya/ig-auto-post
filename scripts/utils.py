"""
utils.py  –  共通ユーティリティ
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

JST = timezone(timedelta(hours=9))

# ---------------------------------------------------------------------------
# ログ
# ---------------------------------------------------------------------------

def get_logger(name: str) -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    return logging.getLogger(name)


# ---------------------------------------------------------------------------
# JSON 読み書き
# ---------------------------------------------------------------------------

def read_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def read_text(path: Path) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read().strip()


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


# ---------------------------------------------------------------------------
# ステータス管理
# ---------------------------------------------------------------------------

def update_status(folder: Path, status: str, extra: dict | None = None) -> None:
    """status.json を更新する。"""
    data = {
        "id": folder.name,
        "status": status,
        "updated_at": datetime.now(JST).isoformat(),
    }
    if extra:
        data.update(extra)
    write_json(folder / "status.json", data)


def get_status(folder: Path) -> str:
    path = folder / "status.json"
    if not path.exists():
        return "unknown"
    return read_json(path).get("status", "unknown")


# ---------------------------------------------------------------------------
# アイデアID 生成
# ---------------------------------------------------------------------------

def new_idea_id() -> str:
    """YYYY-MM-DD_NNN 形式の新しいIDを生成する。"""
    today = datetime.now(JST).strftime("%Y-%m-%d")
    ideas_dir = Path("ideas")
    ideas_dir.mkdir(exist_ok=True)
    existing = [d.name for d in ideas_dir.iterdir() if d.is_dir() and d.name.startswith(today)]
    n = len(existing) + 1
    return f"{today}_{n:03d}"


# ---------------------------------------------------------------------------
# フォルダ探索
# ---------------------------------------------------------------------------

def find_folders_with_status(base_dir: Path, status: str) -> list[Path]:
    """base_dir 以下で指定ステータスのフォルダを返す（古い順）。"""
    result = []
    if not base_dir.exists():
        return result
    for d in sorted(base_dir.iterdir()):
        if d.is_dir() and get_status(d) == status:
            result.append(d)
    return result
