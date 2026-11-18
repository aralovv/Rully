import os
from dotenv import load_dotenv
load_dotenv()
import requests
import json

TOKEN = os.getenv("VERCEL_TOKEN", "")
PROJECT = "rully"
BASE_URL = f"https://api.vercel.com/v10/projects/{PROJECT}/env"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

env_vars = {
    "TURSO_DATABASE_URL": os.getenv("TURSO_DATABASE_URL", ""),
    "TURSO_AUTH_TOKEN": os.getenv("TURSO_AUTH_TOKEN", ""),
    "BOT_TOKEN": os.getenv("BOT_TOKEN", ""),
    "SECRET_KEY": os.getenv("SECRET_KEY", ""),
    "ADMIN_USERNAME": os.getenv("ADMIN_USERNAME", "Anvarjon"),
    "ADMIN_PASSWORD": os.getenv("ADMIN_PASSWORD", ""),
    "ADMIN_TELEGRAM_ID": os.getenv("ADMIN_TELEGRAM_ID", ""),
    "ORDERS_GROUP_CHAT_ID": os.getenv("ORDERS_GROUP_CHAT_ID", "-5464313435"),
    "EXAM_TOTAL_QUESTIONS": os.getenv("EXAM_TOTAL_QUESTIONS", "20"),
    "EXAM_TIME_LIMIT_SECONDS": os.getenv("EXAM_TIME_LIMIT_SECONDS", "1500"),
    "EXAM_PASSING_SCORE": os.getenv("EXAM_PASSING_SCORE", "18"),
    "QUICK_TEST_QUESTIONS": os.getenv("QUICK_TEST_QUESTIONS", "10"),
    "IMAGE_CDN_BASE_URL": os.getenv("IMAGE_CDN_BASE_URL", "https://cdn.jsdelivr.net/gh/aralovv/Rully@main/data/images/original"),
    "WEB_APP_URL": os.getenv("WEB_APP_URL", "https://rully-rully4.vercel.app"),
    "VERCEL": "1"
}

# 1. Get existing env vars
res = requests.get(BASE_URL, headers=headers)
print("Get envs response:", res.status_code)
existing_keys = set()
if res.status_code == 200:
    for env in res.json().get("envs", []):
        existing_keys.add(env.get("key"))
    print("Existing env keys:", existing_keys)

# 2. Add or skip
for k, v in env_vars.items():
    if k in existing_keys:
        print(f"Env '{k}' already exists, skipping.")
        continue

    payload = {
        "key": k,
        "value": v,
        "type": "plain",
        "target": ["production", "preview", "development"]
    }
    post_res = requests.post(BASE_URL, headers=headers, json=payload)
    print(f"Adding '{k}': status {post_res.status_code}")

print("All environment variables synced to Vercel!")
