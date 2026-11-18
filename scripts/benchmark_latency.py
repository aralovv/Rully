import time
import requests

urls = [
    ("Mini App HTML (/)", "https://rully-rully4.vercel.app/"),
    ("Admin HTML (/admin)", "https://rully-rully4.vercel.app/admin"),
    ("Static Admin (/static/admin/index.html)", "https://rully-rully4.vercel.app/static/admin/index.html"),
    ("API Health (/api/health)", "https://rully-rully4.vercel.app/api/health"),
    ("API Categories (/api/categories)", "https://rully-rully4.vercel.app/api/categories"),
]

for label, url in urls:
    times = []
    for _ in range(3):
        t0 = time.time()
        try:
            r = requests.get(url, timeout=15)
            duration = (time.time() - t0) * 1000
            status = r.status_code
        except Exception as e:
            duration = (time.time() - t0) * 1000
            status = f"ERR: {e}"
        times.append(duration)
    avg_t = sum(times) / len(times)
    print(f"{label:<40} | Status: {status} | Times: {[f'{t:.0f}ms' for t in times]} | Avg: {avg_t:.0f}ms")
