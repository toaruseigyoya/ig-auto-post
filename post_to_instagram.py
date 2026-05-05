import os, sys, time, requests
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("IG_ACCESS_TOKEN")
user_id = os.getenv("IG_USER_ID")
image_url = os.getenv("IG_IMAGE_URL")
base = "https://graph.facebook.com/v21.0"

print(f"IG_USER_ID: {user_id}")
print(f"IMAGE_URL: {image_url}")

# Step 1: メディアコンテナ作成
r1 = requests.post(f"{base}/{user_id}/media", data={
    "image_url": image_url,
    "caption": "テスト投稿 #4コマ漫画 #test",
    "access_token": token
}, timeout=30)
print("Step1:", r1.json())
if "error" in r1.json():
    sys.exit(1)
creation_id = r1.json()["id"]

time.sleep(3)

# Step 2: 公開
r2 = requests.post(f"{base}/{user_id}/media_publish", data={
    "creation_id": creation_id,
    "access_token": token
}, timeout=30)
print("Step2:", r2.json())
if "id" in r2.json():
    print("✅ 投稿成功！Instagramで確認してください")
