import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import sqlite3
from src.database import init_db, register_initial_sources
from src.extractors.yesprava_extractor import YesPravaExtractor
from src.extractors.propdd_extractor import ProPDDExtractor

def run_prototype():
    print("==================================================")
    print("PHASE 1: PROTOTYPE EXTRACTION & INTEGRITY CHECK")
    print("==================================================")

    conn = init_db()
    register_initial_sources(conn)

    # 1. YesPrava prototype extraction
    print("\n[1/4] Extracting Prototype Sample from YesPrava (Tickets 1 & 2)...")
    yes_extractor = YesPravaExtractor(conn)
    for lang in ["uz_latn", "ru", "uz_cyrl"]:
        for t in [1, 2]:
            count = yes_extractor.import_ticket(t, lang=lang, download_images=True)
            print(f"  YesPrava: Ticket {t} ({lang}) -> {count} questions imported")

    # 2. ProPDD prototype extraction
    print("\n[2/4] Extracting Prototype Sample from ProPDD (Tickets 1 & 2)...")
    propdd_extractor = ProPDDExtractor(conn)
    for lang in ["uz_latn", "ru", "uz_cyrl"]:
        for t in [1, 2]:
            count = propdd_extractor.import_ticket(t, lang=lang, download_images=True)
            print(f"  ProPDD: Ticket {t} ({lang}) -> {count} questions imported")

    # 3. Database Statistics
    print("\n[3/4] Database Integrity & Statistics Verification:")
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM questions;")
    total_q = cur.fetchone()[0]

    cur.execute("SELECT language, COUNT(*) FROM questions GROUP BY language;")
    lang_counts = cur.fetchall()

    cur.execute("SELECT COUNT(*) FROM answers;")
    total_a = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM images;")
    total_img = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM question_sources;")
    total_qs = cur.fetchone()[0]

    cur.execute("SELECT s.source_code, COUNT(qs.id) FROM sources s LEFT JOIN question_sources qs ON s.id = qs.source_id GROUP BY s.id;")
    source_counts = cur.fetchall()

    print(f"  Total canonical questions: {total_q}")
    print(f"  Language breakdown: {lang_counts}")
    print(f"  Total answer options: {total_a}")
    print(f"  Total unique images acquired: {total_img}")
    print(f"  Total source links tracked: {total_qs}")
    print(f"  Source distribution: {source_counts}")

    # 4. Image file validation on disk
    print("\n[4/4] Verifying image files on disk...")
    cur.execute("SELECT id, filename, sha256, local_path, file_size FROM images LIMIT 5;")
    sample_imgs = cur.fetchall()
    for img in sample_imgs:
        exists = os.path.exists(img[3])
        actual_size = os.path.getsize(img[3]) if exists else 0
        print(f"  Image #{img[0]}: {img[1]} (SHA: {img[2][:8]}...) exists={exists}, size={actual_size} bytes")

    # 5. Sanity Checks
    print("\n[Sanity Check 1] Questions without correct answer:")
    cur.execute("""
        SELECT q.id, q.question_text
        FROM questions q
        LEFT JOIN answers a ON q.id = a.question_id AND a.is_correct = 1
        WHERE a.id IS NULL;
    """)
    missing_correct = cur.fetchall()
    print(f"  Found {len(missing_correct)} questions missing correct answer.")

    print("\n[Sanity Check 2] Questions with fewer than 2 options:")
    cur.execute("""
        SELECT q.id, COUNT(a.id)
        FROM questions q
        LEFT JOIN answers a ON q.id = a.question_id
        GROUP BY q.id
        HAVING COUNT(a.id) < 2;
    """)
    under_opts = cur.fetchall()
    print(f"  Found {len(under_opts)} questions with < 2 options.")

    print("\n[Sanity Check 3] Sample Question Detail:")
    cur.execute("""
        SELECT q.id, q.language, q.question_text, q.explanation, i.local_path
        FROM questions q
        LEFT JOIN images i ON q.image_id = i.id
        WHERE q.image_id IS NOT NULL
        LIMIT 1;
    """)
    sample_row = cur.fetchone()
    if sample_row:
        print(f"  ID: {sample_row[0]}")
        print(f"  Lang: {sample_row[1]}")
        print(f"  Text: {sample_row[2]}")
        print(f"  Explanation: {sample_row[3]}")
        print(f"  Image: {sample_row[4]}")
        cur.execute("SELECT option_key, answer_text, is_correct FROM answers WHERE question_id = ? ORDER BY sort_order;", (sample_row[0],))
        for opt in cur.fetchall():
            star = " [*CORRECT*]" if opt[2] == 1 else ""
            print(f"    {opt[0]}: {opt[1]}{star}")

    conn.close()
    print("\nPhase 1 Prototype Extraction Complete!")

if __name__ == "__main__":
    run_prototype()
