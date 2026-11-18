import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import sqlite3
import time
import requests
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.database import init_db, register_initial_sources
from src.extractors.yesprava_extractor import YesPravaExtractor
from src.extractors.propdd_extractor import ProPDDExtractor

def acquire_yesprava(conn: sqlite3.Connection):
    print("\n" + "="*50, flush=True)
    print("ACQUISITION: YESPRAVA.UZ (63 TICKETS, 3 LANGUAGES)", flush=True)
    print("="*50, flush=True)

    extractor = YesPravaExtractor(conn)
    total_tickets = 63
    languages = ["uz_latn", "ru", "uz_cyrl"]

    # Step 1: Preload all ticket data with ThreadPool
    print("\n[Step 1/3] Pre-fetching YesPrava ticket JSONs (Parallel 8 threads)...", flush=True)
    tickets_cache = {"uz_latn": {}, "ru": {}, "uz_cyrl": {}}
    all_image_urls = set()

    def fetch_ticket_task(lang, t):
        data = extractor.fetch_ticket_json(t, lang=lang)
        return lang, t, data

    tasks = [(l, t) for l in languages for t in range(1, total_tickets + 1)]
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(fetch_ticket_task, l, t) for l, t in tasks]
        done = 0
        for f in as_completed(futures):
            l, t, data = f.result()
            if data and "questions" in data:
                tickets_cache[l][t] = data
                for q in data["questions"]:
                    if q.get("image"):
                        all_image_urls.add(q.get("image"))
            done += 1
            if done % 30 == 0 or done == len(tasks):
                print(f"  Fetched {done}/{len(tasks)} ticket JSONs...", flush=True)

    print(f"Total unique YesPrava images identified: {len(all_image_urls)}", flush=True)

    # Step 2: Batch preload images (Worker threads download, main thread writes to SQLite)
    print("\n[Step 2/3] Downloading YesPrava images in parallel...", flush=True)
    extractor.img_mgr.batch_preload_urls(list(all_image_urls), max_workers=10)

    # Step 3: Insert into database (Fast local insertion)
    print("\n[Step 3/3] Inserting YesPrava questions into SQLite...", flush=True)
    for lang in languages:
        t0 = time.time()
        imported = 0
        cur = conn.cursor()
        for t in range(1, total_tickets + 1):
            data = tickets_cache[lang].get(t)
            if not data:
                continue
            for q in data.get("questions", []):
                orig_id = str(q.get("id"))
                text = q.get("text", "").strip()
                options = q.get("options", [])
                correct_idx = q.get("correct")
                teaser = q.get("teaser")
                cat_name = q.get("category", "Umumiy")
                cat_slug = q.get("topic", "umumiy")
                image_url = q.get("image")

                if not text or not options:
                    continue

                cat_id = extractor.get_or_create_category(cat_slug, cat_name)
                image_id = extractor.img_mgr.url_cache.get(image_url) if image_url else None

                norm_text = " ".join(text.lower().split())
                norm_opts = "|".join(" ".join(opt.lower().split()) for opt in options)
                hash_input = f"{lang}:{norm_text}:{norm_opts}".encode("utf-8")
                canonical_hash = hashlib.sha256(hash_input).hexdigest()
                qid = f"UZ-YHQ-{canonical_hash[:10].upper()}"

                cur.execute("""
                    INSERT INTO questions (id, canonical_hash, question_text, category_id, language, image_id, explanation, verification_status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'SOURCE_CONFIRMED', datetime('now'), datetime('now'))
                    ON CONFLICT(canonical_hash) DO UPDATE SET updated_at = datetime('now')
                """, (qid, canonical_hash, text, cat_id, lang, image_id, teaser))

                cur.execute("DELETE FROM answers WHERE question_id = ?", (qid,))
                for idx, opt_text in enumerate(options):
                    opt_key = chr(ord('A') + idx)
                    is_correct = 1 if idx == correct_idx else 0
                    cur.execute("""
                        INSERT INTO answers (question_id, option_key, answer_text, is_correct, sort_order)
                        VALUES (?, ?, ?, ?, ?)
                    """, (qid, opt_key, opt_text.strip(), is_correct, idx))

                raw_payload = json.dumps(q, ensure_ascii=False)
                cur.execute("""
                    INSERT INTO question_sources (question_id, source_id, original_question_id, original_ticket, original_position, original_url, original_language, collection_timestamp, raw_payload)
                    VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), ?)
                """, (qid, extractor.source_id, orig_id, t, q.get("position"), f"{extractor.base_url}/yhq-savollari/bilet-{t}", lang, raw_payload))
                imported += 1
        conn.commit()
        print(f"  [{lang}] Finished: {imported} questions inserted in {time.time()-t0:.1f}s", flush=True)

def acquire_propdd_chunks(extractor: ProPDDExtractor):
    print("\n--- Pre-fetching ProPDD Image Chunks ---", flush=True)
    chunk_files = list(set(q.get("ib") for q in extractor.questions_data if q.get("ib")))
    print(f"Total unique chunk files to fetch: {len(chunk_files)}", flush=True)

    def fetch_one_chunk(chunk_file):
        url = f"{extractor.base_url}/img/{chunk_file}"
        headers = {"User-Agent": "Mozilla/5.0"}
        for attempt in range(2):
            try:
                r = requests.get(url, headers=headers, timeout=10)
                if r.status_code == 200:
                    return chunk_file, r.json()
            except Exception:
                pass
        return chunk_file, {}

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(fetch_one_chunk, cf): cf for cf in chunk_files}
        done_count = 0
        for future in as_completed(futures):
            cf, data = future.result()
            if data:
                extractor.chunk_cache[cf] = data
            done_count += 1
            if done_count % 50 == 0 or done_count == len(chunk_files):
                print(f"  Cached {done_count}/{len(chunk_files)} image chunks...", flush=True)

def acquire_propdd(conn: sqlite3.Connection):
    print("\n" + "="*50, flush=True)
    print("ACQUISITION: PROPDD.UZ (61 TICKETS, 3 LANGUAGES)", flush=True)
    print("="*50, flush=True)

    extractor = ProPDDExtractor(conn)
    acquire_propdd_chunks(extractor)

    languages = ["uz_latn", "ru", "uz_cyrl"]
    total_tickets = 61

    for lang in languages:
        print(f"\n--- Starting ProPDD language: {lang} ---", flush=True)
        t0 = time.time()
        imported_lang = 0
        for ticket in range(1, total_tickets + 1):
            count = extractor.import_ticket(ticket, lang=lang, download_images=True)
            imported_lang += count
            if ticket % 15 == 0 or ticket == total_tickets:
                print(f"  [{lang}] Ticket {ticket}/{total_tickets} imported. Total: {imported_lang} questions ({time.time()-t0:.1f}s)", flush=True)

def run_all_acquisition():
    conn = init_db()
    register_initial_sources(conn)

    print("\nSTARTING OPTIMIZED FULL MULTI-SOURCE ACQUISITION (PHASE 2)...", flush=True)
    start_time = time.time()

    # 1. Acquire YesPrava
    acquire_yesprava(conn)

    # 2. Acquire ProPDD
    acquire_propdd(conn)

    elapsed_total = time.time() - start_time
    print(f"\nFull acquisition completed in {elapsed_total:.1f}s", flush=True)

    # Final DB Summary
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM questions;")
    total_q = cur.fetchone()[0]

    cur.execute("SELECT language, COUNT(*) FROM questions GROUP BY language;")
    lang_breakdown = cur.fetchall()

    cur.execute("SELECT COUNT(*) FROM images;")
    total_img = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM answers;")
    total_a = cur.fetchone()[0]

    cur.execute("SELECT s.source_code, qs.original_language, COUNT(*) FROM question_sources qs JOIN sources s ON qs.source_id = s.id GROUP BY s.source_code, qs.original_language;")
    source_stats = cur.fetchall()

    print("\n" + "="*50, flush=True)
    print("ACQUISITION SUMMARY")
    print("="*50, flush=True)
    print(f"Total Canonical Questions in DB: {total_q}", flush=True)
    print(f"Language Breakdown: {lang_breakdown}", flush=True)
    print(f"Total Unique Images Acquired: {total_img}", flush=True)
    print(f"Total Answers Stored: {total_a}", flush=True)
    print("Source Breakdown:", flush=True)
    for row in source_stats:
        print(f"  Source: {row[0]}, Lang: {row[1]} -> {row[2]} records", flush=True)

    conn.close()

if __name__ == "__main__":
    run_all_acquisition()
