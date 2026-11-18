import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import requests, json

headers = {'User-Agent': 'Mozilla/5.0'}
r = requests.get('https://propdd.uz/data.js', headers=headers, timeout=10)
text = r.text
prefix = 'window.UZ_QUESTIONS='
if text.startswith(prefix):
    js_data = text[len(prefix):].rstrip('; \n')
    questions = json.loads(js_data)
    print(f"Total questions parsed from propdd.uz: {len(questions)}")
    for i in range(min(5, len(questions))):
        q = questions[i]
        print(f"Index {i}: id={q.get('id')}, t={q.get('t')}, img={q.get('img')}, ib={q.get('ib')}")
        print(f"   lat: {q.get('lat')[0]} | options: {len(q.get('lat')[1])} | correct: {q.get('lat')[2]}")

    # Check unique ib chunks
    ibs = set(q.get('ib') for q in questions if q.get('ib'))
    print(f"Total unique image chunks (ib): {len(ibs)}")
    print(f"Sample ib chunks: {list(ibs)[:10]}")
