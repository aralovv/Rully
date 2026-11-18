import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import requests, json
from bs4 import BeautifulSoup

headers = {'User-Agent': 'Mozilla/5.0'}

r = requests.get('https://osonprava.uz/uz/savollar', headers=headers, timeout=10)
soup = BeautifulSoup(r.text, 'html.parser')
print("osonprava /uz/savollar status:", r.status_code)

# Check links to categories / tickets / questions
links = [a.get('href') for a in soup.find_all('a') if a.get('href')]
savollar_links = [l for l in links if '/savollar' in l]
print(f"Total savollar links on page: {len(savollar_links)}")
print("Sample links:", savollar_links[:10])

# Inspect one of the topics or questions
if savollar_links:
    target = 'https://osonprava.uz' + savollar_links[1] if savollar_links[1].startswith('/') else savollar_links[1]
    print(f"\nFetching {target}")
    r2 = requests.get(target, headers=headers, timeout=10)
    print("Status:", r2.status_code)
    soup2 = BeautifulSoup(r2.text, 'html.parser')
    print("Title:", soup2.title.string if soup2.title else None)
    h1 = soup2.find('h1')
    print("H1:", h1.text.strip() if h1 else None)
    # Check for question elements or Next.js state
    nd = soup2.find('script', id='__NEXT_DATA__')
    if nd and nd.string:
        print("Found __NEXT_DATA__")
    else:
        # Check Next.js app router RSC or inline scripts
        scripts = soup2.find_all('script')
        for s in scripts:
            if s.string and 'self.__next_f' in s.string:
                print("Found App Router self.__next_f stream payload!")
                break
