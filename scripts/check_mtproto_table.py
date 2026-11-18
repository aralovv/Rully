import os
from dotenv import load_dotenv
load_dotenv()
import requests

url = os.getenv("TURSO_DATABASE_URL")
token = os.getenv("TURSO_AUTH_TOKEN")
pipeline_url = f"{url}/v2/pipeline"
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# 1. Pragma table_info
payload = {
    "requests": [
        {"type": "execute", "stmt": {"sql": "PRAGMA table_info(mtproto_accounts)"}},
        {"type": "execute", "stmt": {"sql": "SELECT * FROM mtproto_accounts"}}
    ]
}

res = requests.post(pipeline_url, headers=headers, json=payload)
data = res.json()
print("Columns:")
for row in data["results"][0]["response"]["result"]["rows"]:
    print(" ", [v.get("value") for v in row])

print("\nRows in mtproto_accounts:")
rows = data["results"][1]["response"]["result"]["rows"]
print(f"Total rows: {len(rows)}")
for r in rows:
    print(" ", [v.get("value") for v in r])
