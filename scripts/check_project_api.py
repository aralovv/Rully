import os
from dotenv import load_dotenv
load_dotenv()
import requests
import json

TOKEN = os.getenv("VERCEL_TOKEN", "")
headers = {"Authorization": f"Bearer {TOKEN}"}

res = requests.get("https://api.vercel.com/v9/projects/rully", headers=headers)
print("Project status:", res.status_code)
if res.status_code == 200:
    data = res.json()
    print("Project ID:", data.get("id"))
    print("Project Name:", data.get("name"))
    print("Link:", data.get("link"))
    print("Targets:", data.get("targets"))
