import os
from dotenv import load_dotenv
load_dotenv()
import requests

TOKEN = os.getenv("VERCEL_TOKEN")
headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

payload = {"serverlessFunctionRegion": "bom1"}
res = requests.patch("https://api.vercel.com/v9/projects/rully", headers=headers, json=payload)
print("Status:", res.status_code)
print("Updated region:", res.json().get("serverlessFunctionRegion"))
