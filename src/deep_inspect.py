import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import requests
from bs4 import BeautifulSoup
import json
import xml.etree.ElementTree as ET

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

def inspect_sitemap(url):
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            root = ET.fromstring(r.content)
            # handle namespaces
            urls = []
            for elem in root.iter():
                if elem.tag.endswith('loc') and elem.text:
                    urls.append(elem.text.strip())
            return {"status": 200, "count": len(urls), "sample": urls[:10], "all_urls": urls}
        else:
            return {"status": r.status_code}
    except Exception as e:
        return {"error": str(e)}

print("--- Inspecting yhq-test.uz sitemaps ---")
yhq_sm = inspect_sitemap("https://yhq-test.uz/sitemap.xml")
print(f"yhq-test sitemap count: {yhq_sm.get('count')}")
if yhq_sm.get("sample"):
    print("Sample:", yhq_sm["sample"][:5])

print("\n--- Inspecting yesprava.uz sitemaps ---")
yes_sm = inspect_sitemap("https://yesprava.uz/sitemap.xml")
print(f"yesprava sitemap count: {yes_sm.get('count')}")
if yes_sm.get("sample"):
    print("Sample:", yes_sm["sample"][:5])

print("\n--- Inspecting osonprava.uz sitemaps ---")
oson_sm = inspect_sitemap("https://osonprava.uz/sitemap.xml")
print(f"osonprava sitemap count: {oson_sm.get('count')}")
if oson_sm.get("sample"):
    print("Sample:", oson_sm["sample"][:5])

print("\n--- Inspecting propdd.uz sitemaps ---")
propdd_sm = inspect_sitemap("https://propdd.uz/sitemap.xml")
print(f"propdd sitemap count: {propdd_sm.get('count')}")
if propdd_sm.get("sample"):
    print("Sample:", propdd_sm["sample"][:5])

# Let's inspect Next.js data or question pages
def test_page(url):
    try:
        r = requests.get(url, headers=headers, timeout=10)
        print(f"\nGET {url} -> {r.status_code}, len={len(r.content)}")
        soup = BeautifulSoup(r.text, "html.parser")
        # Check for __NEXT_DATA__
        next_data = soup.find("script", id="__NEXT_DATA__")
        if next_data and next_data.string:
            try:
                data = json.loads(next_data.string)
                page_props = data.get("props", {}).get("pageProps", {})
                print(f"__NEXT_DATA__ keys: {list(page_props.keys())}")
                return page_props
            except Exception as e:
                print("Error parsing next_data:", e)
        # Check for JSON in script tags
        scripts = soup.find_all("script")
        for s in scripts:
            if s.string and ("question" in s.string.lower() or "savol" in s.string.lower()):
                print("Found inline script mentioning question/savol, len=", len(s.string))
                break
    except Exception as e:
        print(f"Error getting {url}: {e}")
    return None

print("\n--- Testing Specific Question Pages ---")
test_page("https://yhq-test.uz/browse")
test_page("https://yesprava.uz/yhq-savollari")
test_page("https://osonprava.uz/uz/savollar")
