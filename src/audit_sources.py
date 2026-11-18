import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import requests
from bs4 import BeautifulSoup
import json
import urllib.parse

urls = {
    "yhq_test": "https://yhq-test.uz",
    "propdd": "https://propdd.uz",
    "pravaonline": "https://pravaonline.uz",
    "avtodars": "https://avtodars.uz",
    "cartest": "https://cartest.uz",
    "osonprava": "https://osonprava.uz",
    "yesprava": "https://yesprava.uz"
}

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

results = {}

for name, base_url in urls.items():
    print(f"\n--- Probing {name}: {base_url} ---")
    site_info = {"base_url": base_url}
    
    # 1. robots.txt
    try:
        r_rob = requests.get(f"{base_url}/robots.txt", headers=headers, timeout=10)
        site_info["robots_status"] = r_rob.status_code
        site_info["robots_preview"] = r_rob.text[:300] if r_rob.status_code == 200 else None
    except Exception as e:
        site_info["robots_status"] = f"Error: {e}"
        
    # 2. Homepage HTML & Title
    try:
        r_home = requests.get(base_url, headers=headers, timeout=15)
        site_info["home_status"] = r_home.status_code
        site_info["final_url"] = r_home.url
        soup = BeautifulSoup(r_home.text, "html.parser")
        site_info["title"] = soup.title.string.strip() if soup.title else None
        
        # Check scripts & links
        scripts = [s.get("src") for s in soup.find_all("script") if s.get("src")]
        links = [a.get("href") for a in soup.find_all("a") if a.get("href")]
        site_info["scripts_sample"] = scripts[:5]
        site_info["internal_links_sample"] = [l for l in links if l.startswith("/") or base_url in l][:10]
        
        # Framework clues
        text_lower = r_home.text.lower()
        frameworks = []
        if "__next" in text_lower or "_next/" in text_lower:
            frameworks.append("Next.js")
        if "__nuxt" in text_lower or "_nuxt/" in text_lower:
            frameworks.append("Nuxt.js")
        if "react" in text_lower:
            frameworks.append("React")
        if "vue" in text_lower:
            frameworks.append("Vue.js")
        if "livewire" in text_lower:
            frameworks.append("Laravel Livewire")
        if "wp-content" in text_lower:
            frameworks.append("WordPress")
        site_info["detected_tech"] = frameworks
        
    except Exception as e:
        site_info["home_status"] = f"Error: {e}"
        
    results[name] = site_info
    print(f"Title: {site_info.get('title')}")
    print(f"Tech: {site_info.get('detected_tech')}")
    print(f"Links sample: {site_info.get('internal_links_sample')}")

with open("data/reports/preliminary_audit.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print("\nAudit summary saved to data/reports/preliminary_audit.json")
