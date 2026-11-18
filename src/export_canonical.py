"""
Export canonical product catalog to JSON and CSV formats.
"""
import os
import sys
import sqlite3
import json
import csv

sys.path.insert(0, os.path.abspath("c:/Users/Администратор/AvtoTest"))
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def export_canonical_catalog(db_path="master_database.sqlite", out_dir="data"):
    os.makedirs(out_dir, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Load all canonical questions
    c.execute("""
    SELECT cq.canonical_id, cq.category_id, cq.category_name, cq.primary_image_id, cq.has_image,
           cq.correct_option_key, cq.legal_reference, cq.legal_act_title, cq.verification_status,
           cq.deduplication_status, cq.source_providers, cq.source_metadata, cq.rights_review_status,
           cq.created_at, cq.updated_at,
           im.local_path as image_path, im.sha256 as image_sha256
    FROM canonical_questions cq
    LEFT JOIN images im ON cq.primary_image_id = im.id
    ORDER BY cq.canonical_id
    """)
    questions = [dict(r) for r in c.fetchall()]

    # Load translations
    c.execute("""
    SELECT canonical_id, language, question_text, explanation, translation_status
    FROM canonical_translations
    ORDER BY canonical_id, language
    """)
    translations_by_id = {}
    for r in c.fetchall():
        qid = r["canonical_id"]
        translations_by_id.setdefault(qid, {})[r["language"]] = {
            "question_text": r["question_text"],
            "explanation": r["explanation"],
            "status": r["translation_status"]
        }

    # Load answers
    c.execute("""
    SELECT canonical_id, option_key, sort_order, is_correct, text_uz_latn, text_uz_cyrl, text_ru
    FROM canonical_answers
    ORDER BY canonical_id, sort_order
    """)
    answers_by_id = {}
    for r in c.fetchall():
        qid = r["canonical_id"]
        answers_by_id.setdefault(qid, []).append({
            "key": r["option_key"],
            "sort_order": r["sort_order"],
            "is_correct": bool(r["is_correct"]),
            "text": {
                "uz_latn": r["text_uz_latn"],
                "uz_cyrl": r["text_uz_cyrl"],
                "ru": r["text_ru"]
            }
        })

    # Assemble JSON objects
    full_catalog = []
    csv_rows = []

    for q in questions:
        qid = q["canonical_id"]
        trans = translations_by_id.get(qid, {})
        ans = answers_by_id.get(qid, [])
        providers = json.loads(q["source_providers"])
        meta = json.loads(q["source_metadata"])

        item = {
            "canonical_id": qid,
            "category": {
                "id": q["category_id"],
                "name": q["category_name"]
            },
            "has_image": bool(q["has_image"]),
            "image": {
                "id": q["primary_image_id"],
                "path": q["image_path"],
                "sha256": q["image_sha256"]
            } if q["has_image"] else None,
            "correct_option_key": q["correct_option_key"],
            "legal": {
                "reference": q["legal_reference"],
                "act_title": q["legal_act_title"],
                "verification_status": q["verification_status"]
            },
            "deduplication_status": q["deduplication_status"],
            "rights_review_status": q["rights_review_status"],
            "source_providers": providers,
            "source_metadata": meta,
            "translations": trans,
            "options": ans,
            "created_at": q["created_at"],
            "updated_at": q["updated_at"]
        }
        full_catalog.append(item)

        # Flat CSV row
        csv_rows.append({
            "canonical_id": qid,
            "category_name": q["category_name"],
            "has_image": 1 if q["has_image"] else 0,
            "image_path": q["image_path"] or "",
            "correct_key": q["correct_option_key"],
            "question_uz_latn": trans.get("uz_latn", {}).get("question_text", ""),
            "question_uz_cyrl": trans.get("uz_cyrl", {}).get("question_text", ""),
            "question_ru": trans.get("ru", {}).get("question_text", ""),
            "options_count": len(ans),
            "legal_reference": q["legal_reference"] or "",
            "verification_status": q["verification_status"],
            "deduplication_status": q["deduplication_status"],
            "sources": ",".join(providers)
        })

    # Write JSON
    json_path = os.path.join(out_dir, "canonical_questions.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(full_catalog, f, ensure_ascii=False, indent=2)

    # Write CSV
    csv_path = os.path.join(out_dir, "canonical_questions.csv")
    if csv_rows:
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(csv_rows[0].keys()))
            writer.writeheader()
            writer.writerows(csv_rows)

    print(f"Exported {len(full_catalog)} canonical items to:")
    print(f"  - {json_path} ({os.path.getsize(json_path)} bytes)")
    print(f"  - {csv_path} ({os.path.getsize(csv_path)} bytes)")
    conn.close()

if __name__ == "__main__":
    export_canonical_catalog()
