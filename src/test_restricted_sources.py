import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import requests

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
}

print("--- Testing pravaonline.uz API endpoints ---")
endpoints = [
    'https://pravaonline.uz/api/v2/tickets?page=0&size=100&sortBy=ticketNumber&direction=ASC',
    'https://pravaonline.uz/api/v1/app/offline-bundle',
    'https://pravaonline.uz/api/v2/tickets/start-visible'
]
for ep in endpoints:
    try:
        r = requests.get(ep, headers=headers, timeout=10)
        print(f"{ep} -> {r.status_code}, len={len(r.content)}")
        if r.status_code == 200:
            print("Preview:", r.text[:200])
    except Exception as e:
        print(f"{ep} -> Error: {e}")

print("\n--- Testing cartest.uz public access ---")
cartest_urls = [
    'https://cartest.uz/api/tickets',
    'https://cartest.uz/test',
    'https://cartest.uz/demo'
]
for u in cartest_urls:
    try:
        r = requests.get(u, headers=headers, timeout=10)
        print(f"{u} -> {r.status_code}, len={len(r.content)}")
    except Exception as e:
        print(f"{u} -> Error: {e}")
