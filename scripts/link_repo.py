import os
from dotenv import load_dotenv
load_dotenv()
import requests
import json

TOKEN = os.getenv("VERCEL_TOKEN", "")
PROJECT_ID = "prj_OwFxG41g6A6vzVNOWuWrVbHFVTOL"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

payload = {
    "type": "github",
    "repo": "aralovv/Rully"
}

res = requests.post(f"https://api.vercel.com/v9/projects/{PROJECT_ID}/link", headers=headers, json=payload)
print("Link status:", res.status_code)
print("Response:", res.text)
