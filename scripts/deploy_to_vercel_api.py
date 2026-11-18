import os
from dotenv import load_dotenv
load_dotenv()
import os
import requests
import json
import base64
import time

TOKEN = os.getenv("VERCEL_TOKEN", "")
PROJECT_NAME = "rully"
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

def collect_files():
    files_to_upload = []

    # 1. Root config files
    for root_file in ["vercel.json", "requirements.txt", "api/index.py"]:
        if os.path.exists(root_file):
            with open(root_file, "r", encoding="utf-8") as f:
                content = f.read()
            files_to_upload.append({
                "file": root_file.replace("\\", "/"),
                "data": content
            })

    # 2. src directory
    for root, dirs, files in os.walk("src"):
        for file in files:
            if file.endswith(".py"):
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, ".").replace("\\", "/")
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                files_to_upload.append({
                    "file": rel_path,
                    "data": content
                })

    # 3. static directory
    for root, dirs, files in os.walk("static"):
        for file in files:
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, ".").replace("\\", "/")
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()
                files_to_upload.append({
                    "file": rel_path,
                    "data": content
                })
            except UnicodeDecodeError:
                with open(full_path, "rb") as f:
                    content_b64 = base64.b64encode(f.read()).decode("utf-8")
                files_to_upload.append({
                    "file": rel_path,
                    "data": content_b64,
                    "encoding": "base64"
                })

    return files_to_upload

def deploy():
    print("Collecting files for Vercel deployment...")
    files = collect_files()
    print(f"Collected {len(files)} files to deploy.")

    # Read vercel.json config
    with open("vercel.json", "r", encoding="utf-8") as f:
        vercel_config = json.load(f)

    payload = {
        "name": PROJECT_NAME,
        "target": "production",
        "files": files,
        "projectSettings": {
            "framework": None
        }
    }

    print(f"Submitting deployment to Vercel API for project '{PROJECT_NAME}'...")
    res = requests.post("https://api.vercel.com/v13/deployments", headers=HEADERS, json=payload)
    print("Deploy response status:", res.status_code)

    if res.status_code in [200, 201]:
        data = res.json()
        dep_id = data.get("id")
        url = data.get("url")
        print(f"Deployment created successfully!")
        print(f"Deployment ID: {dep_id}")
        print(f"URL: https://{url}")
        
        # Check alias
        aliases = data.get("alias", [])
        if aliases:
            print(f"Production Aliases: {', '.join([f'https://{a}' for a in aliases])}")
            
        # Poll build status
        print("\nWaiting for build to finish...")
        for _ in range(30):
            time.sleep(4)
            check_res = requests.get(f"https://api.vercel.com/v13/deployments/{dep_id}", headers=HEADERS)
            if check_res.status_code == 200:
                c_data = check_res.json()
                state = c_data.get("readyState") or c_data.get("status")
                print(f"Build status: {state}")
                if state in ["READY", "ERROR", "CANCELED"]:
                    if state == "READY":
                        print(f"\n[SUCCESS] DEPLOYMENT IS LIVE! Available at: https://{c_data.get('url')}")
                    else:
                        print(f"\nDeployment ended with state: {state}")
                        print("Details:", c_data.get("errorMessage") or c_data.get("error"))
                    break
    else:
        print("Deployment failed:", res.status_code, res.text)

if __name__ == "__main__":
    deploy()
