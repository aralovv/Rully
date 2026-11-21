import pytest
import sqlite3
import os
import hashlib
import json
import csv
import pandas as pd
from PIL import Image

DB_PATH = "master_database.sqlite"

@pytest.fixture(scope="module")
def db_conn():
    assert os.path.exists(DB_PATH), f"Database file {DB_PATH} must exist"
    conn = sqlite3.connect(DB_PATH)
    yield conn
    conn.close()

# 1. Structural Schema Tests
def test_database_tables_exist(db_conn):
    cur = db_conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = {r[0] for r in cur.fetchall()}
    required_tables = {"questions", "answers", "categories", "sources", "question_sources", "images", "verification_records"}
    missing = required_tables - tables
    assert not missing, f"Missing required database tables: {missing}"

def test_sqlite_pragmas_pass(db_conn):
    cur = db_conn.cursor()
    cur.execute("PRAGMA integrity_check;")
    int_check = cur.fetchall()
    assert int_check == [('ok',)], f"PRAGMA integrity_check failed: {int_check}"

    cur.execute("PRAGMA foreign_key_check;")
    fk_check = cur.fetchall()
    assert len(fk_check) == 0, f"PRAGMA foreign_key_check found violations: {fk_check}"

# 2. Complete Question Text & Encoding Validation (ALL questions, NO LIMIT)
def test_all_questions_have_valid_text_and_encoding(db_conn):
    cur = db_conn.cursor()
    cur.execute("SELECT id, question_text, language FROM questions;")
    rows = cur.fetchall()
    assert len(rows) >= 5945, f"Expected at least 5,945 questions, found {len(rows)}"

    for qid, text, lang in rows:
        assert text is not None and text.strip() != "", f"Question {qid} has empty text"
        assert len(text.strip()) >= 5, f"Question {qid} has abnormally short text: '{text}'"
        assert "\ufffd" not in text, f"Question {qid} contains replacement character (corrupted Unicode)"
        assert lang in ("uz_latn", "uz_cyrl", "ru"), f"Question {qid} has invalid language '{lang}'"

# 3. Complete Answer Options Validation
def test_all_answers_valid_and_non_empty(db_conn):
    cur = db_conn.cursor()
    cur.execute("SELECT id, question_id, option_key, answer_text, is_correct FROM answers;")
    answers = cur.fetchall()
    assert len(answers) >= 19472, f"Expected at least 19,472 answers, found {len(answers)}"

    for aid, qid, key, text, is_corr in answers:
        assert text is not None and text.strip() != "", f"Answer #{aid} (QID: {qid}) has empty answer_text"
        assert key in ("A", "B", "C", "D", "E"), f"Answer #{aid} has invalid option_key '{key}'"
        assert is_corr in (0, 1), f"Answer #{aid} has invalid is_correct value '{is_corr}'"

def test_every_question_has_valid_options_count(db_conn):
    cur = db_conn.cursor()
    cur.execute("""
        SELECT q.id, COUNT(a.id)
        FROM questions q
        LEFT JOIN answers a ON q.id = a.question_id
        GROUP BY q.id
        HAVING COUNT(a.id) < 2 OR COUNT(a.id) > 5;
    """)
    invalid_counts = cur.fetchall()
    assert len(invalid_counts) == 0, f"Found {len(invalid_counts)} questions with invalid options count (<2 or >5)"

def test_exactly_one_correct_answer_per_question(db_conn):
    cur = db_conn.cursor()
    cur.execute("""
        SELECT q.id, SUM(a.is_correct)
        FROM questions q
        LEFT JOIN answers a ON q.id = a.question_id
        GROUP BY q.id
        HAVING SUM(a.is_correct) != 1;
    """)
    bad_correct = cur.fetchall()
    assert len(bad_correct) == 0, f"Found {len(bad_correct)} questions that do not have exactly 1 correct answer"

def test_detect_and_bound_duplicate_answer_option_text(db_conn):
    """
    Forensic test: Identifies questions where the raw source website published
    duplicate answer option strings within the same question (known raw source defects).
    Ensures that known raw defects do not exceed the cataloged baseline (9 questions).
    """
    cur = db_conn.cursor()
    cur.execute("""
        SELECT question_id, LOWER(TRIM(answer_text)), COUNT(*)
        FROM answers
        GROUP BY question_id, LOWER(TRIM(answer_text))
        HAVING COUNT(*) > 1;
    """)
    dup_answers = cur.fetchall()
    # Exactly 9 questions have raw source duplicate options from YesPrava/ProPDD
    assert len(dup_answers) == 9, f"Unexpected number of duplicate answer texts: {len(dup_answers)} (expected 9 cataloged raw defects)"

# 4. Image Integrity & Association (ALL 1,423 images, NO LIMIT)
def test_all_1423_images_exist_and_match_sha256(db_conn):
    cur = db_conn.cursor()
    cur.execute("SELECT id, sha256, filename, local_path, file_size FROM images;")
    images = cur.fetchall()
    assert len(images) >= 1423, f"Expected at least 1,423 images in DB, found {len(images)}"

    for img_id, expected_sha, fn, path, size in images:
        actual_path = path if os.path.exists(path) else os.path.join("data", path)
        assert os.path.exists(actual_path), f"Image #{img_id} ({path}) does not exist on disk"
        assert os.path.getsize(actual_path) > 100, f"Image #{img_id} is suspiciously small (<100 B)"

        with open(actual_path, "rb") as f:
            actual_sha = hashlib.sha256(f.read()).hexdigest()
        assert actual_sha == expected_sha, f"Image #{img_id} SHA-256 mismatch: {actual_sha} vs {expected_sha}"

def test_all_1423_images_pillow_readable(db_conn):
    cur = db_conn.cursor()
    cur.execute("SELECT id, local_path FROM images;")
    images = cur.fetchall()
    for img_id, path in images:
        actual_path = path if os.path.exists(path) else os.path.join("data", path)
        try:
            with Image.open(actual_path) as im:
                im.verify()
        except Exception as e:
            pytest.fail(f"Image #{img_id} ({actual_path}) cannot be parsed by Pillow: {e}")

def test_unique_image_hashes_in_database(db_conn):
    cur = db_conn.cursor()
    cur.execute("SELECT COUNT(*), COUNT(DISTINCT sha256) FROM images;")
    tot, dist = cur.fetchone()
    assert tot == dist >= 1423, f"Duplicate image hashes found in DB: {tot} total vs {dist} distinct"

def test_image_question_association_integrity(db_conn):
    cur = db_conn.cursor()
    cur.execute("""
        SELECT q.id, q.image_id
        FROM questions q
        WHERE q.image_id IS NOT NULL AND q.image_id NOT IN (SELECT id FROM images);
    """)
    dangling_imgs = cur.fetchall()
    assert len(dangling_imgs) == 0, f"Found {len(dangling_imgs)} questions referencing non-existent image_id"

# 5. Source Records & No Duplicates (Cleaned Source Traces)
def test_all_questions_traceable_to_sources(db_conn):
    cur = db_conn.cursor()
    cur.execute("""
        SELECT q.id
        FROM questions q
        LEFT JOIN question_sources qs ON q.id = qs.question_id
        WHERE qs.id IS NULL;
    """)
    orphaned = cur.fetchall()
    assert len(orphaned) == 0, f"Found {len(orphaned)} questions without source traceability"

def test_no_duplicate_source_references(db_conn):
    cur = db_conn.cursor()
    cur.execute("""
        SELECT source_id, original_language, original_ticket, original_position, question_id, COUNT(*)
        FROM question_sources
        GROUP BY source_id, original_language, original_ticket, original_position, question_id
        HAVING COUNT(*) > 1;
    """)
    dup_sources = cur.fetchall()
    assert len(dup_sources) == 0, f"Found {len(dup_sources)} duplicate source traces in question_sources"

def test_retained_source_count_matches_expected_clean_count(db_conn):
    cur = db_conn.cursor()
    cur.execute("SELECT COUNT(*) FROM question_sources;")
    total_sources = cur.fetchone()[0]
    assert total_sources >= 7383, f"Expected at least 7,383 clean source traces, found {total_sources}"

# 6. Verification Records Completeness & Status Consistency
def test_verification_status_consistency(db_conn):
    cur = db_conn.cursor()
    cur.execute("""
        SELECT q.id, q.verification_status, vr.verification_status
        FROM questions q
        JOIN verification_records vr ON q.id = vr.question_id
        WHERE q.verification_status != vr.verification_status;
    """)
    mismatches = cur.fetchall()
    assert len(mismatches) == 0, f"Found {len(mismatches)} status mismatches between questions and verification_records"

def test_legal_evidence_completeness_for_verified_questions(db_conn):
    cur = db_conn.cursor()
    cur.execute("""
        SELECT id, question_id, verification_status, legal_act_title, resolution_number, legal_source_url
        FROM verification_records
        WHERE verification_status IN ('LEGAL_REFERENCE_FOUND', 'LEGAL_CONTENT_MATCHED');
    """)
    legal_records = cur.fetchall()
    assert len(legal_records) > 0, "No legally referenced records found"
    for r in legal_records:
        rec_id, qid, vstatus, act_title, res_no, url = r
        assert act_title and act_title.strip(), f"Record #{rec_id} has missing legal_act_title"
        assert res_no and res_no.strip(), f"Record #{rec_id} has missing resolution_number"
        assert url and url.startswith("https://lex.uz"), f"Record #{rec_id} has invalid legal_source_url: '{url}'"

# 7. Complete Deliverables Export Consistency Tests
def test_exports_row_count_and_content_consistency(db_conn):
    # questions.json
    assert os.path.exists("questions.json"), "questions.json must exist"
    with open("questions.json", "r", encoding="utf-8") as f:
        j_data = json.load(f)
    assert len(j_data) == 5945, f"questions.json has {len(j_data)} items (expected 5,945)"

    # questions.csv
    assert os.path.exists("questions.csv"), "questions.csv must exist"
    df_csv = pd.read_csv("questions.csv")
    assert len(df_csv) == 5945, f"questions.csv has {len(df_csv)} rows (expected 5,945)"

    # questions.xlsx
    assert os.path.exists("questions.xlsx"), "questions.xlsx must exist"
    df_xlsx = pd.read_excel("questions.xlsx")
    assert len(df_xlsx) == 5945, f"questions.xlsx has {len(df_xlsx)} rows (expected 5,945)"

    # duplicate_report.csv
    assert os.path.exists("duplicate_report.csv"), "duplicate_report.csv must exist"
    df_dup = pd.read_csv("duplicate_report.csv")
    assert len(df_dup) == 2320, f"duplicate_report.csv has {len(df_dup)} rows (expected 2,320)"

    # verification_report.csv
    assert os.path.exists("verification_report.csv"), "verification_report.csv must exist"
    df_vr = pd.read_csv("verification_report.csv")
    assert len(df_vr) == 5945, f"verification_report.csv has {len(df_vr)} rows (expected 5,945)"

    # source_coverage_report.csv
    assert os.path.exists("source_coverage_report.csv"), "source_coverage_report.csv must exist"
    df_cov = pd.read_csv("source_coverage_report.csv")
    total_src_records = df_cov["total_records"].sum()
    assert total_src_records == 7383, f"source_coverage_report.csv total_records sum is {total_src_records} (expected 7,383)"
