import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import requests, json
from bs4 import BeautifulSoup

headers = {'User-Agent': 'Mozilla/5.0'}
r = requests.get('https://yesprava.uz/yhq-savollari/bilet-1', headers=headers, timeout=10)
soup = BeautifulSoup(r.text, 'html.parser')
nd = soup.find('script', id='__NEXT_DATA__')
data = json.loads(nd.string)
build_id = data.get('buildId')
print(f"yesprava buildId: {build_id}")

# Test fetching bilet 2 directly via _next/data JSON
next_data_url = f"https://yesprava.uz/_next/data/{build_id}/yhq-savollari/bilet-2.json"
print(f"Testing {next_data_url}")
r_json = requests.get(next_data_url, headers=headers, timeout=10)
print(f"Status: {r_json.status_code}, len: {len(r_json.content)}")
if r_json.status_code == 200:
    ticket_data = r_json.json()
    qs = ticket_data.get('pageProps', {}).get('data', {}).get('questions', [])
    print(f"Successfully fetched bilet-2 JSON directly! Questions count: {len(qs)}")
    print(f"First question: {qs[0].get('text')}")

# Also test Russian and Cyrillic
next_ru = f"https://yesprava.uz/_next/data/{build_id}/ru/bilety-pdd/bilet-2.json"
r_ru = requests.get(next_ru, headers=headers, timeout=10)
print(f"Russian bilet-2 status: {r_ru.status_code}, len: {len(r_ru.content)}")
if r_ru.status_code == 200:
    qs_ru = r_ru.json().get('pageProps', {}).get('data', {}).get('questions', [])
    print(f"Russian first question: {qs_ru[0].get('text')}")
