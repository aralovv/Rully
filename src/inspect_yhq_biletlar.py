import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import requests, xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

headers = {'User-Agent': 'Mozilla/5.0'}
r = requests.get('https://yhq-test.uz/sitemap.xml', headers=headers, timeout=10)
root = ET.fromstring(r.content)
bilet_urls = [e.text.strip() for e in root.iter() if e.tag.endswith('loc') and e.text and '/biletlar/' in e.text]
print(f"yhq-test.uz has {len(bilet_urls)} /biletlar/ URLs")
print("Sample bilet URLs:", bilet_urls[:5])

if bilet_urls:
    sample_bilet = bilet_urls[0]
    r_b = requests.get(sample_bilet, headers=headers, timeout=10)
    print(f"\nGET {sample_bilet} -> {r_b.status_code}")
    soup = BeautifulSoup(r_b.text, 'html.parser')
    print("Title:", soup.title.string if soup.title else None)
    # Check question links in bilet
    q_links = [a.get('href') for a in soup.find_all('a') if a.get('href') and '/savollar/' in a.get('href')]
    print(f"Question links in bilet ({len(q_links)}):", q_links[:5])
