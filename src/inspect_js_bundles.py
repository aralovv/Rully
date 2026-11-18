import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import requests, re
from bs4 import BeautifulSoup

headers = {'User-Agent': 'Mozilla/5.0'}

# 1. pravaonline bundle
try:
    r_po = requests.get('https://pravaonline.uz/assets/index-BgNRiWuQ.js', headers=headers, timeout=15)
    print('pravaonline JS size:', len(r_po.text))
    api_matches = re.findall(r'https?://[^\s\"\'\`]+|/api/[^\s\"\'\`]+', r_po.text)
    api_filtered = [u for u in set(api_matches) if 'api' in u or 'prava' in u or 'test' in u]
    print('pravaonline relevant APIs/URLs:', api_filtered[:15])
except Exception as e:
    print('pravaonline error:', e)

# 2. avtodars demo test
try:
    r_ad = requests.get('https://avtodars.uz/', headers=headers, timeout=15)
    soup_ad = BeautifulSoup(r_ad.text, 'html.parser')
    demo_sec = soup_ad.find(id='demo-test')
    if demo_sec:
        print('\navtodars demo-test section text:')
        print(demo_sec.get_text('\n', strip=True)[:500])
    # check script tags in avtodars
    for s in soup_ad.find_all('script'):
        if s.string and ('savol' in s.string or 'test' in s.string):
            print('avtodars found script with savol/test, len=', len(s.string))
            print(s.string[:300])
except Exception as e:
    print('avtodars error:', e)

# 3. propdd trainer
try:
    r_pdd = requests.get('https://propdd.uz/trainer', headers=headers, timeout=20)
    print('\npropdd /trainer status:', r_pdd.status_code, 'len:', len(r_pdd.text))
    soup_pdd = BeautifulSoup(r_pdd.text, 'html.parser')
    print('propdd /trainer title:', soup_pdd.title.string.strip() if soup_pdd.title else None)
    # check tickets list
    tickets = [a.get('href') for a in soup_pdd.find_all('a') if a.get('href') and ('bilet' in a.get('href') or 'ticket' in a.get('href') or 'test' in a.get('href'))]
    print('propdd ticket links:', tickets[:10])
    # check scripts
    for s in soup_pdd.find_all('script'):
        if s.get('src'):
            print('script src:', s.get('src'))
        elif s.string and len(s.string) > 20:
            print('inline script preview:', s.string[:200])
except Exception as e:
    print('propdd error:', e)
