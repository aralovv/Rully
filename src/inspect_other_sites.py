import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import requests
from bs4 import BeautifulSoup

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
}

def inspect_site(name, url):
    print(f"\n=================== {name}: {url} ===================")
    try:
        r = requests.get(url, headers=headers, timeout=20)
        print(f"Status: {r.status_code}, Length: {len(r.content)}")
        soup = BeautifulSoup(r.text, 'html.parser')
        print(f"Title: {soup.title.string.strip() if soup.title else None}")
        
        # Look for buttons, links, APIs, scripts
        scripts = [s.get('src') for s in soup.find_all('script') if s.get('src')]
        print(f"Scripts ({len(scripts)}): {scripts[:5]}")
        
        links = [a.get('href') for a in soup.find_all('a') if a.get('href')]
        print(f"Links ({len(links)}): {links[:10]}")
        
        # Check text keywords
        text = soup.get_text()
        keywords = ['bilet', 'test', 'savol', 'imtihon', 'baza', 'yhq', 'pdd']
        found = {k: text.lower().count(k) for k in keywords}
        print(f"Keyword counts: {found}")
    except Exception as e:
        print(f"Error inspecting {name}: {e}")

inspect_site("propdd", "https://propdd.uz/")
inspect_site("pravaonline", "https://pravaonline.uz/")
inspect_site("avtodars", "https://avtodars.uz/")
inspect_site("cartest", "https://cartest.uz/")
