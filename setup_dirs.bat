@echo off
chcp 65001 > nul
cd /d "%~dp0"

echo ============================================
echo   Instagram 自動投稿システム セットアップ
echo ============================================
echo.

REM ディレクトリ作成
mkdir ideas 2>nul
mkdir drafts 2>nul
mkdir approved 2>nul
mkdir posted 2>nul
mkdir public\images\ig 2>nul
mkdir scripts 2>nul
mkdir .github\workflows 2>nul

REM scripts/__init__.py 作成
echo. > scripts\__init__.py

REM Pillow インストール
echo Pillow をインストール中...
pip install Pillow python-dotenv requests

echo.
echo ✅ セットアップ完了！
echo.
echo 使い方:
echo   1. python add_idea.py         ... ネタを登録する
echo   2. python scripts\generate_content.py --id [ID]  ... 下書きを生成
echo   3. drafts\[ID]\ を確認・修正
echo   4. python scripts\approve_content.py --id [ID]   ... 承認
echo   5. python scripts\post_to_instagram.py           ... 投稿！
echo.
pause
