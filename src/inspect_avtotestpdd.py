import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import requests, re
from bs4 import BeautifulSoup

headers = {'User-Agent': 'Mozilla/5.0'}
r = requests.get('https://avtotestpdd.uz/uz', headers=headers, timeout=10)
soup = BeautifulSoup(r.text, 'html.parser')
links = [a.get('href') for a in soup.find_all('a') if a.get('href')]
print('Links on avtotestpdd.uz/uz:', links)
buttons = [b.text.strip() for b in soup.find_all('button')]
print('Buttons:', buttons[:10])
