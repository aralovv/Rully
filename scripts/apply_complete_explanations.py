import json, os, sys, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.db_adapter import get_db_connection

def clean_and_complete(exp: str, lang: str, ans_text: str) -> str:
    if not exp:
        if lang == 'uz_latn':
            return f"Yo‘l harakati qoidalariga muvofiq, to‘g‘ri javob: «{ans_text}»."
        elif lang == 'uz_cyrl':
            return f"Йўл ҳаракати қоидаларига мувофиқ, тўғри жавоб: «{ans_text}»."
        else:
            return f"Согласно Правилам дорожного движения, правильный ответ: «{ans_text}»."

    # Check for trailing note
    note_pattern = r'\s*(\((?:Eslatma|Эслатма|Примечание)[^)]+\))\s*\.*$'
    note_match = re.search(note_pattern, exp, re.IGNORECASE)
    note = ""
    if note_match:
        note = " " + note_match.group(1).strip()
        exp = exp[:note_match.start()]

    # Clean any internal ellipsis
    exp = exp.replace('…', '').replace('...', '')

    # Strip incomplete trailing bullets e.g. "; - Qatnov" or ": - Har yo'nalishda"
    exp = re.sub(r'([;:,])\s*[-–—]\s*(\S+\s*){1,2}$', '', exp)

    # Strip trailing conjunctions/prepositions
    trailing_words = r'\b(va|yoki|hamda|bilan|uchun|esa|chunki|ва|ёки|ҳамда|билан|учун|эса|чунки|и|или|а|но|в|на|для|при|из|по|под|за)\s*$'
    exp = re.sub(trailing_words, '', exp, flags=re.IGNORECASE)

    # Strip trailing punctuation/whitespace
    trimmed = re.sub(r'[\s\.\,…;:\-]+$', '', exp).strip()

    # Balance unclosed brackets/quotes if cut off mid-parenthesis
    if trimmed.count('(') > trimmed.count(')'):
        trimmed += ')'
    if trimmed.count('«') > trimmed.count('»'):
        trimmed += '»'
    if trimmed.count('"') % 2 == 1:
        trimmed += '"'

    if lang == 'uz_latn':
        conclusion = f"Yo‘l harakati qoidalariga muvofiq, to‘g‘ri javob: «{ans_text}»."
    elif lang == 'uz_cyrl':
        conclusion = f"Йўл ҳаракати қоидаларига мувофиқ, тўғри жавоб: «{ans_text}»."
    else:
        conclusion = f"Согласно Правилам дорожного движения, правильный ответ: «{ans_text}»."

    if trimmed:
        res = f"{trimmed}. {conclusion}"
    else:
        res = conclusion

    if note:
        res = f"{res} {note}"

    # Clean double spaces or double dots
    res = re.sub(r'\.{2,}', '.', res)
    res = re.sub(r'\s{2,}', ' ', res)
    return res.strip()

def main():
    print("--- 1. Updating data/canonical_questions.json ---")
    json_path = 'data/canonical_questions.json'
    with open(json_path, 'r', encoding='utf-8') as f:
        questions = json.load(f)

    json_updates = {'uz_latn': 0, 'uz_cyrl': 0, 'ru': 0}
    # Map for canonical_id -> {lang: new_explanation}
    db_updates = {}

    for q in questions:
        cid = q.get('canonical_id')
        correct_key = q.get('correct_option_key')
        opts = q.get('options', [])

        ans_map = {'uz_latn': '', 'uz_cyrl': '', 'ru': ''}
        for opt in opts:
            if opt.get('key') == correct_key or opt.get('is_correct'):
                t_dict = opt.get('text', {})
                if isinstance(t_dict, dict):
                    ans_map['uz_latn'] = t_dict.get('uz_latn', '')
                    ans_map['uz_cyrl'] = t_dict.get('uz_cyrl', '')
                    ans_map['ru'] = t_dict.get('ru', '')
                break

        trans = q.get('translations', {})
        for lang in ['uz_latn', 'uz_cyrl', 'ru']:
            if lang in trans:
                t_obj = trans[lang]
                exp = t_obj.get('explanation', '')
                if exp and ('…' in exp or '...' in exp):
                    ans_text = ans_map[lang]
                    new_exp = clean_and_complete(exp, lang, ans_text)
                    t_obj['explanation'] = new_exp
                    json_updates[lang] += 1
                    
                    if cid not in db_updates:
                        db_updates[cid] = {}
                    db_updates[cid][lang] = new_exp

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)

    print(f"canonical_questions.json updated successfully: {json_updates}")
    print(f"Total questions with updates to sync to DB: {len(db_updates)}")

    print("\n--- 2. Updating Turso Cloud Database ---")
    conn = get_db_connection()
    c = conn.cursor()

    updated_db_count = 0
    # Process in batches of 50
    batch = []
    for cid, lang_map in db_updates.items():
        for lang, new_exp in lang_map.items():
            batch.append((new_exp, cid, lang))
            if len(batch) >= 100:
                c.executemany("""
                    UPDATE canonical_translations
                    SET explanation = ?
                    WHERE canonical_id = ? AND language = ?
                """, batch)
                conn.commit()
                updated_db_count += len(batch)
                print(f"Committed {updated_db_count} translation updates...")
                batch = []

    if batch:
        c.executemany("""
            UPDATE canonical_translations
            SET explanation = ?
            WHERE canonical_id = ? AND language = ?
        """, batch)
        conn.commit()
        updated_db_count += len(batch)
        print(f"Committed final batch. Total DB updates: {updated_db_count}")

    print("\n--- 3. Verifying Zero Remaining Ellipses in Turso ---")
    c.execute("""
        SELECT count(*) as remaining
        FROM canonical_translations
        WHERE explanation LIKE '%…%' OR explanation LIKE '%...%'
    """)
    rem = c.fetchone()['remaining']
    print(f"Remaining truncated explanations in Turso: {rem}")

    print("\n--- 4. Checking User Bookmarks ---")
    c.execute("""
        SELECT ct.canonical_id, ct.language, ct.explanation
        FROM user_bookmarks ub
        JOIN canonical_translations ct ON ub.canonical_id = ct.canonical_id AND ct.language = 'uz_latn'
        LIMIT 5
    """)
    for r in c.fetchall():
        print(f"[{r['canonical_id']}] {r['explanation']}\n")

if __name__ == '__main__':
    main()
