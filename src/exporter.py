import sys, os
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
if hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import sqlite3
import json
import csv
import re
import shutil
import pandas as pd
from typing import Dict, List, Any

class Exporter:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def export_all(self):
        print("\n" + "="*50)
        print("EXPORT ENGINE: GENERATING MASTER DELIVERABLES")
        print("="*50)

        os.makedirs("data/exports", exist_ok=True)
        os.makedirs("data/reports", exist_ok=True)

        cur = self.conn.cursor()

        # 1. Load Sources Registry
        print("[1/6] Exporting source_registry.json...")
        cur.execute("SELECT id, source_code, source_name, source_url, source_type, authority_level, access_method, terms_status, created_at FROM sources;")
        sources_list = []
        sources_dict = {}
        for r in cur.fetchall():
            s_obj = {
                "id": r[0],
                "source_code": r[1],
                "source_name": r[2],
                "source_url": r[3],
                "source_type": r[4],
                "authority_level": r[5],
                "access_method": r[6],
                "terms_status": r[7],
                "created_at": r[8]
            }
            sources_list.append(s_obj)
            sources_dict[r[0]] = s_obj

        with open("source_registry.json", "w", encoding="utf-8") as f:
            json.dump(sources_list, f, ensure_ascii=False, indent=2)
        shutil.copy("source_registry.json", "data/exports/source_registry.json")

        # 2. Source Coverage Report
        print("[2/6] Generating source_coverage_report.csv...")
        cur.execute("""
            SELECT s.source_code, s.source_name, qs.original_language, COUNT(DISTINCT qs.question_id) as unique_questions, COUNT(qs.id) as total_records
            FROM sources s
            LEFT JOIN question_sources qs ON s.id = qs.source_id
            GROUP BY s.id, qs.original_language
            ORDER BY s.id, qs.original_language;
        """)
        cov_rows = cur.fetchall()
        cov_path = "data/reports/source_coverage_report.csv"
        with open(cov_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["source_code", "source_name", "language", "unique_questions", "total_records"])
            for r in cov_rows:
                writer.writerow([r[0], r[1], r[2] or "N/A", r[3], r[4]])
        shutil.copy(cov_path, "source_coverage_report.csv")

        # 3. Compile Master Questions Data
        print("[3/6] Compiling unified questions dataset...")
        cur.execute("""
            SELECT q.id, q.canonical_hash, q.question_text, q.language, q.explanation, q.verification_status,
                   c.name as category_name, i.filename as image_filename, i.local_path as image_local_path
            FROM questions q
            LEFT JOIN categories c ON q.category_id = c.id
            LEFT JOIN images i ON q.image_id = i.id
            ORDER BY q.id;
        """)
        raw_questions = cur.fetchall()

        # Load answers
        cur.execute("SELECT question_id, option_key, answer_text, is_correct, sort_order FROM answers ORDER BY question_id, sort_order;")
        answers_map: Dict[str, List[Dict[str, Any]]] = {}
        for row in cur.fetchall():
            qid = row[0]
            answers_map.setdefault(qid, []).append({
                "key": row[1],
                "text": row[2],
                "is_correct": bool(row[3])
            })

        # Load sources per question
        cur.execute("SELECT question_id, source_id, original_question_id, original_ticket, original_position, original_url, original_language FROM question_sources;")
        qsources_map: Dict[str, List[Dict[str, Any]]] = {}
        for row in cur.fetchall():
            qid = row[0]
            src_info = sources_dict.get(row[1], {})
            qsources_map.setdefault(qid, []).append({
                "source_name": src_info.get("source_name", "Unknown"),
                "source_code": src_info.get("source_code", "unknown"),
                "original_ticket": row[3],
                "original_position": row[4],
                "original_url": row[5],
                "language": row[6]
            })

        json_records = []
        csv_rows = []

        for q in raw_questions:
            qid, qhash, text, lang, expl, vstatus, cat, img_fn, img_path = q
            ans_list = answers_map.get(qid, [])
            src_list = qsources_map.get(qid, [])

            rel_image_path = f"images/original/{img_fn}" if img_fn else None

            # JSON object
            j_obj = {
                "id": qid,
                "canonical_hash": qhash,
                "question_text": text,
                "language": lang,
                "answers": ans_list,
                "image": rel_image_path,
                "category": cat or "General",
                "explanation": expl,
                "verification_status": vstatus,
                "sources": src_list
            }
            json_records.append(j_obj)

            # CSV / Excel flat representation
            clean_str = lambda s: re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", str(s)) if s else ""
            correct_answers = [clean_str(a["text"]) for a in ans_list if a["is_correct"]]
            all_options = " || ".join(f"[{a['key']}] {clean_str(a['text'])}" for a in ans_list)
            csv_rows.append({
                "id": qid,
                "question_text": clean_str(text),
                "language": lang,
                "category": clean_str(cat or "General"),
                "correct_answer": correct_answers[0] if correct_answers else "",
                "options": all_options,
                "image": rel_image_path or "",
                "explanation": clean_str(expl or ""),
                "verification_status": vstatus,
                "sources_count": len(src_list)
            })

        # 4. Export JSON
        print(f"[4/6] Writing questions.json ({len(json_records)} records)...")
        with open("questions.json", "w", encoding="utf-8") as f:
            json.dump(json_records, f, ensure_ascii=False, indent=2)
        shutil.copy("questions.json", "data/exports/questions.json")

        # 5. Export CSV
        print(f"[5/6] Writing questions.csv ({len(csv_rows)} rows)...")
        df = pd.DataFrame(csv_rows)
        df.to_csv("questions.csv", index=False, encoding="utf-8-sig")
        shutil.copy("questions.csv", "data/exports/questions.csv")

        # 6. Export XLSX
        print(f"[6/6] Writing questions.xlsx...")
        df.to_excel("questions.xlsx", index=False, engine="openpyxl")
        shutil.copy("questions.xlsx", "data/exports/questions.xlsx")

        # Copy duplicate and verification reports to root for top-level access
        if os.path.exists("data/reports/duplicate_report.csv"):
            shutil.copy("data/reports/duplicate_report.csv", "duplicate_report.csv")
        if os.path.exists("data/reports/verification_report.csv"):
            shutil.copy("data/reports/verification_report.csv", "verification_report.csv")

        # Copy SQLite DB to root
        shutil.copy("data/master_database.sqlite", "master_database.sqlite")

        print("Master exports generated successfully:")
        print("  - master_database.sqlite")
        print("  - questions.json")
        print("  - questions.csv")
        print("  - questions.xlsx")
        print("  - source_registry.json")
        print("  - duplicate_report.csv")
        print("  - verification_report.csv")
        print("  - source_coverage_report.csv")

if __name__ == "__main__":
    from src.database import init_db
    conn = init_db()
    exporter = Exporter(conn)
    exporter.export_all()
    conn.close()
