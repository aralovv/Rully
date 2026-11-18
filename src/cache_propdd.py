import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import requests, os, time

dest = "data/sources/propdd_data.js"
if os.path.exists(dest) and os.path.getsize(dest) > 1000000:
    print(f"{dest} already exists ({os.path.getsize(dest)} bytes)")
else:
    headers = {'User-Agent': 'Mozilla/5.0'}
    for attempt in range(3):
        try:
            print(f"Downloading propdd.uz/data.js (attempt {attempt+1})...")
            r = requests.get('https://propdd.uz/data.js', headers=headers, timeout=35)
            if r.status_code == 200:
                with open(dest, "w", encoding="utf-8") as f:
                    f.write(r.text)
                print(f"Saved {dest} ({len(r.text)} chars)")
                break
        except Exception as e:
            print(f"Attempt {attempt+1} failed: {e}")
            time.sleep(2)
