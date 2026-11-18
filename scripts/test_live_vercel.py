import sys
import requests

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

url = 'https://rully-rully4.vercel.app'

print("1. Index / Mini App:")
r = requests.get(f"{url}/", timeout=15)
print("  Status:", r.status_code, "Length:", len(r.text))

print("\n2. Health check:")
r = requests.get(f"{url}/api/health", timeout=15)
print("  Status:", r.status_code, r.text)

print("\n3. Categories from Turso on Vercel:")
r = requests.get(f"{url}/api/categories", timeout=15)
print("  Status:", r.status_code)
if r.status_code == 200:
    cats = r.json().get("categories", [])
    print(f"  Categories retrieved: {len(cats)}")
    for c in cats[:3]:
        print(f"    - {c['category_id']}: {c['name']} ({c['question_count']} questions)")

print("\n4. Admin panel:")
r = requests.get(f"{url}/admin", timeout=15)
print("  Status:", r.status_code, "Length:", len(r.text))
