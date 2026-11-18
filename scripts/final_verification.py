import requests

endpoints = [
    "https://rully-rully4.vercel.app/api/health",
    "https://rully-rully4.vercel.app/api/categories",
    "https://rully-rully4.vercel.app/api/telegram-webhook/info",
    "https://cdn.jsdelivr.net/gh/aralovv/Rully@main/data/images/original/0001_1.webp"
]

for url in endpoints:
    try:
        r = requests.get(url, timeout=10)
        print(f"[{r.status_code}] {url} -> Content-Type: {r.headers.get('content-type', '')[:30]}")
    except Exception as e:
        print(f"[ERR] {url}: {e}")
