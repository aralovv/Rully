import os
from dotenv import load_dotenv
load_dotenv()
import requests
import json

TOKEN = os.getenv("VERCEL_TOKEN", "")
headers = {"Authorization": f"Bearer {TOKEN}"}

res = requests.get("https://api.vercel.com/v6/deployments?limit=3", headers=headers)
if res.status_code == 200:
    deps = res.json().get("deployments", [])
    print(f"Total deployments found: {len(deps)}")
    for d in deps:
        print(f"ID: {d.get('uid')}")
        print(f"Name: {d.get('name')}")
        print(f"URL: https://{d.get('url')}")
        print(f"State: {d.get('state')} / {d.get('readyState')}")
        print(f"Created: {d.get('created')}")
        print("-" * 40)
else:
    print("Error querying deployments:", res.status_code, res.text)
