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
    "TURSO_DATABASE_URL": "https://rully-aralovv.aws-ap-south-1.turso.io",
    "TURSO_AUTH_TOKEN": "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3OTUwMDczOTYsImlkIjoiMDFhMWVlYzMtNmUwMS03MWJlLTlkMjEtNzAzMjQ0NDY1MDIzIiwia2lkIjoiMlYxQjFiOWpfUDFLWEFjemlRVDdyc0JRODZDQnB0OTUxYWJMRV9Kajd4QSIsInJpZCI6IjRlNjc5N2RlLWJjYWUtNGRkOS04YmNkLWQ3MDIwOWQyNmExOSJ9.Nyrki10bjIRZAd-J6wSZ0mQX84mGl_xzo1B3oJ-Apjy09ScmNKptlteNcPbhAKJMedVELY46I-iLbTpGGGFBBw",
    "BOT_TOKEN": "8657532177:AAGsyMFpzuwPus9jOdFRNP8f65qa8E-4q8g",
    "SECRET_KEY": "rully_secure_secret_key_32_bytes_minimum_for_crypto_production_2026",
    "ADMIN_USERNAME": "Anvarjon",
    "ADMIN_PASSWORD": "Anvarjon2007!@",
    "ADMIN_TELEGRAM_ID": "1956239701",
    "ORDERS_GROUP_CHAT_ID": "-5464313435",
    "EXAM_TOTAL_QUESTIONS": "20",
    "EXAM_TIME_LIMIT_SECONDS": "1500",
    "EXAM_PASSING_SCORE": "18",
    "QUICK_TEST_QUESTIONS": "10",
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
