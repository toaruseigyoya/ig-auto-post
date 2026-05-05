@echo off
cd /d "%~dp0"

echo === removing old .git ===
if exist ".git" rmdir /s /q ".git"

echo === git init ===
git init -b main

echo === git config ===
git config user.email "jyunya545@gmail.com"
git config user.name "toaruseigyoya"

echo === set remote ===
git remote add origin https://github.com/toaruseigyoya/ig-auto-post.git

echo === git commit ===
git add -A
git commit -m "initial commit"

echo === git push ===
git push -u origin main

if errorlevel 1 (
    echo ERROR: push failed.
    pause
    exit /b 1
)

echo.
echo === DONE ===
pause
