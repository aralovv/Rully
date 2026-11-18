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

# Try disabling ssoProtection
for val in [None, False, {"deploymentType": "disabled"}]:
    res = requests.patch(
        f"https://api.vercel.com/v9/projects/{PROJECT_ID}",
        headers=headers,
        json={"ssoProtection": val}
    )
    print(f"Setting ssoProtection={val}: status {res.status_code}")
    if res.status_code == 200:
        print("Updated successfully!")
        print("ssoProtection now:", res.json().get("ssoProtection"))
        break
    else:
        print("Error:", res.text)
