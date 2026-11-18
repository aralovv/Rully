import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import requests, json
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET

headers = {'User-Agent': 'Mozilla/5.0'}

# 1. Inspect yhq-test.uz actual savollar URLs
r_yhq = requests.get('https://yhq-test.uz/sitemap.xml', headers=headers, timeout=10)
root_yhq = ET.fromstring(r_yhq.content)
yhq_savollar = [e.text.strip() for e in root_yhq.iter() if e.tag.endswith('loc') and e.text and '/savollar/' in e.text]
print(f"yhq-test.uz has {len(yhq_savollar)} /savollar/ URLs")
print("Sample yhq savollar URLs:", yhq_savollar[:5])

if yhq_savollar:
    sample_url = yhq_savollar[0]
    r = requests.get(sample_url, headers=headers, timeout=10)
    print(f"\nGET {sample_url} -> {r.status_code}")
    soup = BeautifulSoup(r.text, 'html.parser')
    print("Title:", soup.title.string if soup.title else None)
    
    # Check LD+JSON
    for ld in soup.find_all('script', type='application/ld+json'):
        try:
            ld_data = json.loads(ld.string)
            print("LD+JSON type:", ld_data.get('@type'))
            print("LD+JSON preview:", json.dumps(ld_data, ensure_ascii=False)[:300])
        except Exception as e:
            print("LD parse err:", e)
            
    # Check main content
    h1 = soup.find('h1')
    print("H1:", h1.text.strip() if h1 else None)
    # Check options
    options = [btn.text.strip() for btn in soup.find_all(['button', 'li', 'div']) if 'variant' in str(btn.get('class')) or 'option' in str(btn.get('class'))]
    print("Options sample:", options[:4])
    imgs = [img.get('src') for img in soup.find_all('img') if img.get('src')]
    print("Images:", imgs)
