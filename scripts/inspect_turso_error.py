import os
from dotenv import load_dotenv
load_dotenv()
import requests

url = os.getenv("TURSO_DATABASE_URL")
token = os.getenv("TURSO_AUTH_TOKEN")

pipeline_url = f"{url}/v2/pipeline"
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
payload = {
    "requests": [
        {"type": "execute", "stmt": {"sql": "SELECT id, phone_number, tg_username, tg_first_name, is_active FROM mtproto_accounts"}}
    ]
}

res = requests.post(pipeline_url, headers=headers, json=payload)
print("Status code:", res.status_code)
print("Response JSON:", res.json())
