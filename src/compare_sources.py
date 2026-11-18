import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import json

with open("data/sources/propdd_data.js", "r", encoding="utf-8") as f:
    text = f.read()

prefix = "window.UZ_QUESTIONS="
questions = json.loads(text[len(prefix):].rstrip("; \n"))
print(f"Total questions in propdd: {len(questions)}")

found_count = 0
for q in questions:
    txt = q.get("lat", [""])[0].lower()
    if "transport vositalariga qaysi" in txt:
        found_count += 1
        print(f"Match #{found_count}: id={q.get('id')}, ticket={q.get('t')}: {q.get('lat')[0]}")
        print(f"   Options: {q.get('lat')[1]}")
        print(f"   Correct index: {q.get('lat')[2]} ({q.get('lat')[1][q.get('lat')[2]]})")
