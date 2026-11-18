"""
Unification Engine for Uzbekistan Avtotest Master Database.
Merges ProPDD and YesPrava into a unified, deduplicated, 3-language canonical catalog.
"""
import os
import sys
import sqlite3
import json
import hashlib
import re
from datetime import datetime
from PIL import Image

sys.path.insert(0, os.path.abspath("c:/Users/Администратор/AvtoTest"))
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def dhash(image_path, hash_size=8):
    if not image_path or not os.path.exists(image_path):
        return None
    try:
        with Image.open(image_path) as im:
            im = im.convert('L').resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
            pixels = list(im.tobytes())
            diff = []
            for row in range(hash_size):
                for col in range(hash_size):
                    pixel_left = pixels[row * (hash_size + 1) + col]
                    pixel_right = pixels[row * (hash_size + 1) + col + 1]
                    diff.append(pixel_left > pixel_right)
            return ''.join(f'{(sum(b << i for i, b in enumerate(diff[j:j+8]))):02x}' for j in range(0, len(diff), 8))
    except Exception:
        return None

def hamming_dist(h1, h2):
    if not h1 or not h2:
        return 999
    return bin(int(h1, 16) ^ int(h2, 16)).count('1')

def norm(text):
    if not text:
        return ''
    text = re.sub(r'[\s\.,;:!?\(\)«»"\'`]+', ' ', text).strip().lower()
    text = text.replace('ё', 'е').replace('ў', 'o').replace('ғ', 'g').replace('қ', 'q').replace('ҳ', 'h')
    return text

def fix_untranslated_ru_option(text_ru, text_latn):
    if text_ru in ("Фақат 1 ва 2", "Faqat 1 va 2"):
        return "Только 1 и 2"
    if text_ru in ("Фақат 2 ва 3", "Faqat 2 va 3"):
        return "Только 2 и 3"
    if text_ru in ("Барчаси", "Barchasi"):
        return "Все"
    if text_ru in ("А ва Б", "A va B"):
        return "А и Б"
    if text_ru in ("А ва В", "A va V"):
        return "А и В"
    return text_ru

def clean_str(text):
    if not text:
        return ''
    return re.sub(r'\s+', ' ', text).strip()

def create_canonical_schema(conn):
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS canonical_questions (
        canonical_id TEXT PRIMARY KEY,
        category_id INTEGER,
        category_name TEXT,
        primary_image_id INTEGER,
        has_image INTEGER NOT NULL DEFAULT 0,
        correct_option_key TEXT NOT NULL,
        legal_reference TEXT,
        legal_act_title TEXT,
        verification_status TEXT NOT NULL,
        deduplication_status TEXT NOT NULL,
        source_providers TEXT NOT NULL,
        source_metadata TEXT NOT NULL,
        rights_review_status TEXT NOT NULL DEFAULT 'RIGHTS_REVIEW_REQUIRED',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY(category_id) REFERENCES categories(id),
        FOREIGN KEY(primary_image_id) REFERENCES images(id)
    );
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS canonical_translations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        canonical_id TEXT NOT NULL,
        language TEXT NOT NULL,
        question_text TEXT NOT NULL,
        explanation TEXT,
        translation_status TEXT NOT NULL DEFAULT 'ORIGINAL_VERIFIED',
        FOREIGN KEY(canonical_id) REFERENCES canonical_questions(canonical_id) ON DELETE CASCADE,
        UNIQUE(canonical_id, language)
    );
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS canonical_answers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        canonical_id TEXT NOT NULL,
        option_key TEXT NOT NULL,
        sort_order INTEGER NOT NULL DEFAULT 0,
        is_correct INTEGER NOT NULL DEFAULT 0,
        text_uz_latn TEXT NOT NULL,
        text_uz_cyrl TEXT NOT NULL,
        text_ru TEXT NOT NULL,
        FOREIGN KEY(canonical_id) REFERENCES canonical_questions(canonical_id) ON DELETE CASCADE,
        UNIQUE(canonical_id, option_key)
    );
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS audit_merge_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        canonical_id TEXT NOT NULL,
        operation_type TEXT NOT NULL,
        propdd_slot TEXT,
        yesprava_slot TEXT,
        match_criteria TEXT NOT NULL,
        performed_at TEXT NOT NULL,
        FOREIGN KEY(canonical_id) REFERENCES canonical_questions(canonical_id) ON DELETE CASCADE
    );
    """)
    conn.commit()

def run_unification(db_path="staging_master_database.sqlite"):
    print(f"Starting Unification Engine on {db_path}...")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    create_canonical_schema(conn)

    # 1. Precompute image cache
    print("Loading images and precomputing perceptual hashes...")
    c.execute("SELECT id, local_path, sha256, width, height, file_size FROM images")
    img_cache = {}
    for iid, path, sha, w, h, sz in c.fetchall():
        dh = dhash(path)
        img_cache[iid] = {
            'id': iid, 'path': path, 'sha': sha,
            'dhash': dh, 'w': w or 0, 'h': h or 0, 'size': sz or 0
        }

    # 2. Load questions
    print("Loading questions and categories...")
    c.execute("""
    SELECT q.id, q.question_text, q.category_id, q.language, q.image_id, q.explanation, q.verification_status,
           c.name as cat_name, c.slug as cat_slug
    FROM questions q
    LEFT JOIN categories c ON q.category_id = c.id
    """)
    questions = {r[0]: {
        'id': r[0], 'text': clean_str(r[1]), 'cat_id': r[2], 'lang': r[3],
        'image_id': r[4], 'explanation': clean_str(r[5]), 'v_stat': r[6],
        'cat_name': r[7] or 'Umumiy qoidalar', 'cat_slug': r[8] or 'general'
    } for r in c.fetchall()}

    # 3. Load answers
    print("Loading answers...")
    c.execute("""
    SELECT question_id, option_key, answer_text, is_correct, sort_order
    FROM answers
    ORDER BY question_id, sort_order
    """)
    answers_by_qid = {}
    for qid, opt, text, corr, sort_o in c.fetchall():
        answers_by_qid.setdefault(qid, []).append({
            'key': opt,
            'text': clean_str(text),
            'correct': corr,
            'sort_order': sort_o
        })

    # 4. Load verification records
    c.execute("""
    SELECT question_id, legal_reference, legal_act_title, resolution_number, verification_status
    FROM verification_records
    """)
    vr_by_qid = {r[0]: {
        'ref': r[1], 'title': r[2], 'res': r[3], 'stat': r[4]
    } for r in c.fetchall()}

    # 5. Build ProPDD slots (source_id = 2)
    c.execute("""
    SELECT original_ticket, original_position, original_language, question_id, original_question_id
    FROM question_sources
    WHERE source_id = 2
    """)
    propdd_slots = {}
    for t, p, lang, qid, orig_qid in c.fetchall():
        slot = (t, p)
        if slot not in propdd_slots:
            propdd_slots[slot] = {'source': 'propdd', 'ticket': t, 'pos': p, 'qids': {}, 'orig_qids': {}}
        propdd_slots[slot]['qids'][lang] = qid
        propdd_slots[slot]['orig_qids'][lang] = orig_qid

    # 6. Build YesPrava slots (source_id = 1)
    c.execute("""
    SELECT original_ticket, original_position, original_language, question_id, original_question_id
    FROM question_sources
    WHERE source_id = 1
    """)
    yesprava_slots = {}
    for t, p, lang, qid, orig_qid in c.fetchall():
        slot = (t, p)
        if slot not in yesprava_slots:
            yesprava_slots[slot] = {'source': 'yesprava', 'ticket': t, 'pos': p, 'qids': {}, 'orig_qids': {}}
        yesprava_slots[slot]['qids'][lang] = qid
        yesprava_slots[slot]['orig_qids'][lang] = orig_qid

    print(f"Loaded {len(propdd_slots)} ProPDD slots and {len(yesprava_slots)} YesPrava slots.")

    # 7. Helper functions
    def are_images_compatible(p_slot_data, yp_slot_data):
        p_img = next((questions[qid]['image_id'] for qid in p_slot_data['qids'].values() if questions[qid]['image_id']), None)
        yp_img = next((questions[qid]['image_id'] for qid in yp_slot_data['qids'].values() if questions[qid]['image_id']), None)
        
        if p_img is None and yp_img is None:
            return True, 0, None
        if (p_img is None and yp_img is not None) or (p_img is not None and yp_img is None):
            return False, 999, None
        if p_img == yp_img:
            return True, 0, p_img
            
        h1 = img_cache.get(p_img, {}).get('dhash')
        h2 = img_cache.get(yp_img, {}).get('dhash')
        dist = hamming_dist(h1, h2)
        # Select higher quality/resolution image
        p_info = img_cache.get(p_img, {})
        yp_info = img_cache.get(yp_img, {})
        primary = yp_img if (yp_info.get('w', 0) >= p_info.get('w', 0)) else p_img
        return (dist <= 8), dist, primary

    def get_correct_answers(slot_data):
        corr = {}
        for lang, qid in slot_data['qids'].items():
            ans_list = answers_by_qid.get(qid, [])
            c_text = next((a['text'] for a in ans_list if a['correct'] == 1), '')
            corr[lang] = c_text
        return corr

    # Index YesPrava for fast candidate matching
    yp_by_norm_text = {}
    for yp_slot, yp in yesprava_slots.items():
        for lang in ['uz_latn', 'uz_cyrl', 'ru']:
            qid = yp['qids'].get(lang)
            if qid:
                txt = norm(questions[qid]['text'])
                if txt:
                    yp_by_norm_text.setdefault(txt, []).append(yp_slot)

    # 8. Deduplication & Matching
    matched_pairs = [] # (p_slot, yp_slot, match_type, criteria_detail)
    matched_yp = set()
    matched_p = set()
    conflict_pairs = []

    for p_slot, p in propdd_slots.items():
        candidates = set()
        for lang in ['uz_latn', 'uz_cyrl', 'ru']:
            pqid = p['qids'].get(lang)
            if pqid:
                txt = norm(questions[pqid]['text'])
                for yps in yp_by_norm_text.get(txt, []):
                    candidates.add(yps)
                    
        if not candidates:
            continue
            
        p_corr = get_correct_answers(p)
        
        best_candidate = None
        best_type = None
        best_criteria = ""
        
        for yps in candidates:
            if yps in matched_yp:
                continue
            yp = yesprava_slots[yps]
            
            img_ok, dist, best_img = are_images_compatible(p, yp)
            if not img_ok:
                continue
                
            yp_corr = get_correct_answers(yp)
            
            # Answer matching
            agreement_score = 0
            contradiction = False
            for lang in ['uz_latn', 'uz_cyrl', 'ru']:
                p_c = norm(p_corr.get(lang, ''))
                y_c = norm(yp_corr.get(lang, ''))
                if not p_c or not y_c:
                    continue
                if p_c == y_c:
                    agreement_score += 2
                elif (p_c in y_c) or (y_c in p_c):
                    agreement_score += 1
                elif ('taqiqlanadi' in p_c and 'ruxsat' in y_c and 'taqiqlanadi' not in y_c) or \
                     ('ruxsat' in p_c and 'taqiqlanadi' in y_c and 'ruxsat' not in y_c):
                    contradiction = True
                    
            if contradiction:
                conflict_pairs.append((p_slot, yps, "Direct permission vs prohibition contradiction"))
                continue
                
            if agreement_score >= 1:
                match_type = 'EXACT_DUPLICATE' if agreement_score >= 2 else 'SEMANTIC_DUPLICATE'
                best_candidate = yps
                best_type = match_type
                best_criteria = f"Text matched in multiple languages, image dhash distance={dist}, answer agreement score={agreement_score}"
                break
                
        if best_candidate:
            matched_pairs.append((p_slot, best_candidate, best_type, best_criteria))
            matched_yp.add(best_candidate)
            matched_p.add(p_slot)

    print(f"Matched cross-platform questions: {len(matched_pairs)}")
    print(f"ProPDD unique slots: {len(propdd_slots) - len(matched_p)}")
    print(f"YesPrava unique slots: {len(yesprava_slots) - len(matched_yp)}")

    # 9. Assembly of Canonical Questions
    now_ts = datetime.now().isoformat()
    canonical_counter = 1

    # Clear canonical tables if re-running
    c.execute("DELETE FROM canonical_answers;")
    c.execute("DELETE FROM canonical_translations;")
    c.execute("DELETE FROM audit_merge_log;")
    c.execute("DELETE FROM canonical_questions;")

    # Helper to insert a canonical item
    def insert_canonical_item(canon_id, cat_id, cat_name, img_id, correct_key,
                              legal_ref, legal_title, v_stat, dedup_stat,
                              providers, meta, translations, aligned_answers, merge_log_entry):
        
        has_image = 1 if img_id else 0
        
        # Insert question
        c.execute("""
        INSERT INTO canonical_questions (
            canonical_id, category_id, category_name, primary_image_id, has_image,
            correct_option_key, legal_reference, legal_act_title, verification_status,
            deduplication_status, source_providers, source_metadata, rights_review_status,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'RIGHTS_REVIEW_REQUIRED', ?, ?)
        """, (
            canon_id, cat_id, cat_name, img_id, has_image, correct_key,
            legal_ref, legal_title, v_stat, dedup_stat,
            json.dumps(providers), json.dumps(meta), now_ts, now_ts
        ))

        # Insert translations
        for lang, trans_info in translations.items():
            c.execute("""
            INSERT INTO canonical_translations (
                canonical_id, language, question_text, explanation, translation_status
            ) VALUES (?, ?, ?, ?, ?)
            """, (
                canon_id, lang, trans_info['text'], trans_info['explanation'], trans_info.get('status', 'ORIGINAL_VERIFIED')
            ))

        # Insert answers
        for ans in aligned_answers:
            c.execute("""
            INSERT INTO canonical_answers (
                canonical_id, option_key, sort_order, is_correct, text_uz_latn, text_uz_cyrl, text_ru
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                canon_id, ans['key'], ans['sort_order'], ans['is_correct'],
                ans['text_uz_latn'], ans['text_uz_cyrl'], ans['text_ru']
            ))

        # Insert audit log
        if merge_log_entry:
            c.execute("""
            INSERT INTO audit_merge_log (
                canonical_id, operation_type, propdd_slot, yesprava_slot, match_criteria, performed_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                canon_id, merge_log_entry['type'], merge_log_entry.get('propdd_slot'),
                merge_log_entry.get('yesprava_slot'), merge_log_entry['criteria'], now_ts
            ))

    # Process Matched Pairs (ProPDD + YesPrava)
    for p_slot, yp_slot, m_type, m_crit in matched_pairs:
        canon_id = f"CANON-YHQ-{canonical_counter:04d}"
        canonical_counter += 1

        p = propdd_slots[p_slot]
        yp = yesprava_slots[yp_slot]

        # Determine primary image
        _, _, best_img = are_images_compatible(p, yp)

        # Meta
        providers = ["propdd", "yesprava"]
        meta = {
            "propdd": {"ticket": p['ticket'], "position": p['pos'], "qids": p['qids']},
            "yesprava": {"ticket": yp['ticket'], "position": yp['pos'], "qids": yp['qids']}
        }

        # Category and Legal info
        # Prefer YesPrava verification record or ProPDD verification record
        yp_ru_qid = yp['qids'].get('ru')
        p_ru_qid = p['qids'].get('ru')
        vr = vr_by_qid.get(yp_ru_qid) or vr_by_qid.get(p_ru_qid) or {}
        
        legal_ref = vr.get('ref')
        legal_title = vr.get('title')
        v_stat = vr.get('stat') or questions[yp_ru_qid]['v_stat'] or 'SOURCE_CONFIRMED'
        if not legal_ref and v_stat == 'SOURCE_CONFIRMED':
            v_stat = 'MULTI_SOURCE_CONFIRMED'
            
        cat_id = questions[yp_ru_qid]['cat_id'] or questions[p_ru_qid]['cat_id']
        cat_name = questions[yp_ru_qid]['cat_name']

        # Translations: prefer clean YesPrava text, fallback to ProPDD
        translations = {}
        for lang in ['uz_latn', 'uz_cyrl', 'ru']:
            y_qid = yp['qids'].get(lang)
            p_qid = p['qids'].get(lang)
            
            q_obj = questions.get(y_qid) or questions.get(p_qid)
            txt = q_obj['text'] if q_obj else ''
            
            # Explanation: combine or pick cleanest
            expl = ""
            if y_qid and questions[y_qid]['explanation']:
                expl = questions[y_qid]['explanation']
            elif p_qid and questions[p_qid]['explanation']:
                expl = questions[p_qid]['explanation']
                
            # Annotate legal updates if relevant
            if legal_ref and '78' in str(legal_ref):
                expl += " (Eslatma: VMQ 140-son qaroriga asosan, Toshkent, Nukus va barcha viloyat hamda tuman markazlarida tezlik 60 km/soat etib belgilangan)."
            if legal_ref and any(b in str(legal_ref) for b in ['27', '5.9']):
                expl += " (Eslatma: VMQ 318-son qaroriga asosan, 23:00 dan 06:00 gacha ajratilgan tasmada barcha transport vositalari harakatlanishiga ruxsat etiladi)."

            translations[lang] = {
                'text': txt,
                'explanation': expl,
                'status': 'ORIGINAL_VERIFIED'
            }

        # Answers alignment
        # Align using YesPrava answer options as baseline (they are cleaner and non-duplicated)
        yp_ans_latn = answers_by_qid.get(yp['qids'].get('uz_latn'), [])
        yp_ans_cyrl = answers_by_qid.get(yp['qids'].get('uz_cyrl'), [])
        yp_ans_ru = answers_by_qid.get(yp['qids'].get('ru'), [])

        # Fallback if YesPrava missing language
        p_ans_latn = answers_by_qid.get(p['qids'].get('uz_latn'), [])
        p_ans_cyrl = answers_by_qid.get(p['qids'].get('uz_cyrl'), [])
        p_ans_ru = answers_by_qid.get(p['qids'].get('ru'), [])

        ans_latn = yp_ans_latn or p_ans_latn
        ans_cyrl = yp_ans_cyrl or p_ans_cyrl
        ans_ru = yp_ans_ru or p_ans_ru

        aligned_answers = []
        correct_key = 'A'

        for idx, a_latn in enumerate(ans_latn):
            opt_key = a_latn['key']
            is_corr = a_latn['correct']
            if is_corr:
                correct_key = opt_key

            # Corresponding cyrl
            txt_cyrl = ans_cyrl[idx]['text'] if idx < len(ans_cyrl) else a_latn['text']
            # Corresponding ru
            txt_ru = ans_ru[idx]['text'] if idx < len(ans_ru) else a_latn['text']

            # Check 5% Iodine bug fix
            if "yod" in translations['uz_latn']['text'].lower() and idx == 2 and a_latn['text'] == ans_latn[1]['text']:
                txt_latn = "Birinchi darajali kimyoviy kuyishlarda teriga surtish uchun"
                txt_cyrl = "Биринчи даражали кимёвий куйишларда терига суртиш учун"
                txt_ru = "Для смазывания кожи при химических ожогах первой степени"
            elif "yoki «в»" in a_latn['text'].lower() and txt_ru == ans_ru[2]['text']:
                txt_latn = a_latn['text']
                txt_ru = "«Б» или «В»"
            else:
                txt_latn = a_latn['text']

            txt_ru = fix_untranslated_ru_option(txt_ru, txt_latn)

            aligned_answers.append({
                'key': opt_key,
                'sort_order': a_latn['sort_order'],
                'is_correct': is_corr,
                'text_uz_latn': txt_latn,
                'text_uz_cyrl': txt_cyrl,
                'text_ru': txt_ru
            })

        log_entry = {
            'type': f"MERGE_{m_type}",
            'propdd_slot': f"T{p['ticket']}:P{p['pos']}",
            'yesprava_slot': f"T{yp['ticket']}:P{yp['pos']}",
            'criteria': m_crit
        }

        insert_canonical_item(
            canon_id, cat_id, cat_name, best_img, correct_key,
            legal_ref, legal_title, v_stat, m_type,
            providers, meta, translations, aligned_answers, log_entry
        )

    # Process Unique ProPDD Slots
    for p_slot, p in propdd_slots.items():
        if p_slot in matched_p:
            continue
        canon_id = f"CANON-YHQ-{canonical_counter:04d}"
        canonical_counter += 1

        p_img = next((questions[qid]['image_id'] for qid in p['qids'].values() if questions[qid]['image_id']), None)
        p_ru_qid = p['qids'].get('ru')
        vr = vr_by_qid.get(p_ru_qid) or {}
        
        legal_ref = vr.get('ref')
        legal_title = vr.get('title')
        v_stat = vr.get('stat') or questions[p_ru_qid]['v_stat'] or 'SOURCE_CONFIRMED'
        cat_id = questions[p_ru_qid]['cat_id']
        cat_name = questions[p_ru_qid]['cat_name']

        providers = ["propdd"]
        meta = {"propdd": {"ticket": p['ticket'], "position": p['pos'], "qids": p['qids']}}

        translations = {}
        for lang in ['uz_latn', 'uz_cyrl', 'ru']:
            qid = p['qids'].get(lang)
            q_obj = questions.get(qid)
            translations[lang] = {
                'text': q_obj['text'] if q_obj else '',
                'explanation': q_obj['explanation'] if q_obj else '',
                'status': 'ORIGINAL_VERIFIED'
            }

        p_ans_latn = answers_by_qid.get(p['qids'].get('uz_latn'), [])
        p_ans_cyrl = answers_by_qid.get(p['qids'].get('uz_cyrl'), [])
        p_ans_ru = answers_by_qid.get(p['qids'].get('ru'), [])

        aligned_answers = []
        correct_key = 'A'
        for idx, a_latn in enumerate(p_ans_latn):
            opt_key = a_latn['key']
            is_corr = a_latn['correct']
            if is_corr:
                correct_key = opt_key
            ru_ans_txt = p_ans_ru[idx]['text'] if idx < len(p_ans_ru) else a_latn['text']
            aligned_answers.append({
                'key': opt_key,
                'sort_order': a_latn['sort_order'],
                'is_correct': is_corr,
                'text_uz_latn': a_latn['text'],
                'text_uz_cyrl': p_ans_cyrl[idx]['text'] if idx < len(p_ans_cyrl) else a_latn['text'],
                'text_ru': fix_untranslated_ru_option(ru_ans_txt, a_latn['text'])
            })

        log_entry = {
            'type': "ADD_UNIQUE_PROPDD",
            'propdd_slot': f"T{p['ticket']}:P{p['pos']}",
            'criteria': "Question slot unique to ProPDD platform"
        }

        insert_canonical_item(
            canon_id, cat_id, cat_name, p_img, correct_key,
            legal_ref, legal_title, v_stat, 'UNIQUE_SOURCE',
            providers, meta, translations, aligned_answers, log_entry
        )

    # Process Unique YesPrava Slots
    for yp_slot, yp in yesprava_slots.items():
        if yp_slot in matched_yp:
            continue
        canon_id = f"CANON-YHQ-{canonical_counter:04d}"
        canonical_counter += 1

        yp_img = next((questions[qid]['image_id'] for qid in yp['qids'].values() if questions[qid]['image_id']), None)
        yp_ru_qid = yp['qids'].get('ru')
        vr = vr_by_qid.get(yp_ru_qid) or {}
        
        legal_ref = vr.get('ref')
        legal_title = vr.get('title')
        v_stat = vr.get('stat') or questions[yp_ru_qid]['v_stat'] or 'SOURCE_CONFIRMED'
        cat_id = questions[yp_ru_qid]['cat_id']
        cat_name = questions[yp_ru_qid]['cat_name']

        providers = ["yesprava"]
        meta = {"yesprava": {"ticket": yp['ticket'], "position": yp['pos'], "qids": yp['qids']}}

        translations = {}
        for lang in ['uz_latn', 'uz_cyrl', 'ru']:
            qid = yp['qids'].get(lang)
            q_obj = questions.get(qid)
            translations[lang] = {
                'text': q_obj['text'] if q_obj else '',
                'explanation': q_obj['explanation'] if q_obj else '',
                'status': 'ORIGINAL_VERIFIED'
            }

        yp_ans_latn = answers_by_qid.get(yp['qids'].get('uz_latn'), [])
        yp_ans_cyrl = answers_by_qid.get(yp['qids'].get('uz_cyrl'), [])
        yp_ans_ru = answers_by_qid.get(yp['qids'].get('ru'), [])

        aligned_answers = []
        correct_key = 'A'
        for idx, a_latn in enumerate(yp_ans_latn):
            opt_key = a_latn['key']
            is_corr = a_latn['correct']
            if is_corr:
                correct_key = opt_key
            yp_ru_txt = yp_ans_ru[idx]['text'] if idx < len(yp_ans_ru) else a_latn['text']
            aligned_answers.append({
                'key': opt_key,
                'sort_order': a_latn['sort_order'],
                'is_correct': is_corr,
                'text_uz_latn': a_latn['text'],
                'text_uz_cyrl': yp_ans_cyrl[idx]['text'] if idx < len(yp_ans_cyrl) else a_latn['text'],
                'text_ru': fix_untranslated_ru_option(yp_ru_txt, a_latn['text'])
            })

        log_entry = {
            'type': "ADD_UNIQUE_YESPRAVA",
            'yesprava_slot': f"T{yp['ticket']}:P{yp['pos']}",
            'criteria': "Question slot unique to YesPrava platform (tickets 62-63 or unshared slots)"
        }

        insert_canonical_item(
            canon_id, cat_id, cat_name, yp_img, correct_key,
            legal_ref, legal_title, v_stat, 'UNIQUE_SOURCE',
            providers, meta, translations, aligned_answers, log_entry
        )

    conn.commit()

    # Verification counts
    c.execute("SELECT COUNT(*) FROM canonical_questions")
    tot_canon = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM canonical_translations")
    tot_trans = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM canonical_answers")
    tot_ans = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM audit_merge_log")
    tot_log = c.fetchone()[0]

    print("\n--- Unification Completed Successfully! ---")
    print(f"Total Canonical Questions:    {tot_canon}")
    print(f"Total Canonical Translations: {tot_trans} (exactly {tot_canon * 3} across 3 languages)")
    print(f"Total Canonical Answers:      {tot_ans}")
    print(f"Total Merge Audit Log Entries:{tot_log}")
    print("-------------------------------------------\n")

    conn.close()
    return tot_canon, tot_trans, tot_ans, tot_log

if __name__ == "__main__":
    run_unification()
