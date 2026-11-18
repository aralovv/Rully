import os
from dotenv import load_dotenv
load_dotenv()
import requests

TOKEN = os.getenv("VERCEL_TOKEN")
headers = {"Authorization": f"Bearer {TOKEN}"}

res = requests.get("https://api.vercel.com/v9/projects/rully", headers=headers)
data = res.json()
print("Project name:", data.get("name"))
print("Serverless function region:", data.get("serverlessFunctionRegion"))
