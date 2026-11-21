"""
Automated QA & Acceptance Test Suite for the Unified 3-Language Avtotest Question Database & Product Engine.
"""
import pytest
import sqlite3
import os
import json
from PIL import Image
from src.avtotest_product import AvtotestProductEngine, SUPPORTED_LANGUAGES

DB_PATH = "master_database.sqlite"

@pytest.fixture(scope="module")
def db_conn():
    assert os.path.exists(DB_PATH), f"Database file {DB_PATH} must exist"
    conn = sqlite3.connect(DB_PATH)
    yield conn
    conn.close()

@pytest.fixture(scope="module")
def engine():
    return AvtotestProductEngine(DB_PATH)

# 1. Schema & Table Tests
def test_canonical_tables_exist(db_conn):
    cur = db_conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = {r[0] for r in cur.fetchall()}
    required = {"canonical_questions", "canonical_translations", "canonical_answers", "audit_merge_log"}
    missing = required - tables
    assert not missing, f"Missing required canonical tables: {missing}"

def test_database_pragmas_pass(db_conn):
    cur = db_conn.cursor()
    cur.execute("PRAGMA integrity_check;")
    assert cur.fetchall() == [('ok',)], "PRAGMA integrity_check failed"
    cur.execute("PRAGMA foreign_key_check;")
    fk_violations = cur.fetchall()
    assert len(fk_violations) == 0, f"Foreign key violations found: {fk_violations}"

# 2. Canonical Counts & 3-Language Completeness
def test_canonical_questions_count(db_conn):
    cur = db_conn.cursor()
    cur.execute("SELECT COUNT(*) FROM canonical_questions;")
    count = cur.fetchone()[0]
    assert count >= 1295, f"Expected at least 1,295 canonical questions, found {count}"

def test_canonical_translations_complete(db_conn):
    cur = db_conn.cursor()
    cur.execute("SELECT COUNT(*) FROM canonical_questions;")
    total_cq = cur.fetchone()[0]
    cur.execute("""
    SELECT language, COUNT(*) 
    FROM canonical_translations 
    GROUP BY language;
    """)
    lang_counts = dict(cur.fetchall())
    assert lang_counts.get("uz_latn") == total_cq, f"Missing uz_latn translations: {lang_counts}"
    assert lang_counts.get("uz_cyrl") == total_cq, f"Missing uz_cyrl translations: {lang_counts}"
    assert lang_counts.get("ru") == total_cq, f"Missing ru translations: {lang_counts}"

def test_no_empty_question_texts(db_conn):
    cur = db_conn.cursor()
    cur.execute("""
    SELECT COUNT(*) 
    FROM canonical_translations 
    WHERE question_text IS NULL OR trim(question_text) = '';
    """)
    empty_cnt = cur.fetchone()[0]
    assert empty_cnt == 0, f"Found {empty_cnt} empty canonical question texts"

# 3. Canonical Answer Integrity & Alignment
def test_each_question_has_valid_answers_and_single_correct_key(db_conn):
    cur = db_conn.cursor()
    cur.execute("SELECT COUNT(*) FROM canonical_questions;")
    total_cq = cur.fetchone()[0]
    cur.execute("""
    SELECT cq.canonical_id, cq.correct_option_key,
           COUNT(ca.id) as option_count,
           SUM(ca.is_correct) as correct_count
    FROM canonical_questions cq
    JOIN canonical_answers ca ON cq.canonical_id = ca.canonical_id
    GROUP BY cq.canonical_id;
    """)
    rows = cur.fetchall()
    assert len(rows) == total_cq, f"Every question must have answers (expected {total_cq}, got {len(rows)})"
    for qid, corr_key, opt_count, corr_count in rows:
        assert 2 <= opt_count <= 5, f"{qid} has abnormal option count {opt_count}"
        assert corr_count == 1, f"{qid} has {corr_count} correct answers (must be exactly 1)"

def test_correct_option_key_matches_is_correct(db_conn):
    cur = db_conn.cursor()
    cur.execute("""
    SELECT cq.canonical_id, cq.correct_option_key, ca.option_key
    FROM canonical_questions cq
    JOIN canonical_answers ca ON cq.canonical_id = ca.canonical_id AND ca.is_correct = 1
    WHERE cq.correct_option_key != ca.option_key;
    """)
    mismatches = cur.fetchall()
    assert len(mismatches) == 0, f"Found mismatches between correct_option_key and is_correct=1: {mismatches}"

# 4. Zero Duplicate Options (Regression Verification)
def test_zero_duplicate_options_in_all_languages(db_conn):
    cur = db_conn.cursor()
    for col in ["text_uz_latn", "text_uz_cyrl", "text_ru"]:
        cur.execute(f"""
        SELECT canonical_id, {col}, COUNT(*)
        FROM canonical_answers
        GROUP BY canonical_id, lower(trim({col}))
        HAVING COUNT(*) > 1;
        """)
        dups = cur.fetchall()
        assert len(dups) == 0, f"Found duplicate options in {col}: {dups}"

def test_iodine_question_repaired(db_conn):
    cur = db_conn.cursor()
    cur.execute("""
    SELECT ca.option_key, ca.text_uz_latn, ca.text_ru, ca.is_correct
    FROM canonical_questions cq
    JOIN canonical_translations ct ON cq.canonical_id = ct.canonical_id AND ct.language = 'uz_latn'
    JOIN canonical_answers ca ON cq.canonical_id = ca.canonical_id
    WHERE ct.question_text LIKE '%yod nastoykasi%' OR ct.question_text LIKE '%yod eritmasi%'
    ORDER BY ca.sort_order;
    """)
    options = cur.fetchall()
    assert len(options) == 3, f"Expected 3 options for iodine question, got {len(options)}"
    opt_texts_latn = [o[1] for o in options]
    assert len(set(opt_texts_latn)) == 3, f"Iodine options must be unique: {opt_texts_latn}"
    # Verify option C is authentic distractor
    assert "kimyoviy kuyish" in opt_texts_latn[2].lower(), "Option C must be authentic chemical burn distractor"

# 5. Image Linking & Filesystem Readability
def test_canonical_images_exist_and_readable(db_conn):
    cur = db_conn.cursor()
    cur.execute("""
    SELECT cq.canonical_id, im.local_path
    FROM canonical_questions cq
    JOIN images im ON cq.primary_image_id = im.id
    WHERE cq.has_image = 1;
    """)
    rows = cur.fetchall()
    assert len(rows) > 700, f"Expected >700 image questions, got {len(rows)}"
    for qid, path in rows:
        assert os.path.exists(path), f"Image file missing for {qid}: {path}"
        with Image.open(path) as img:
            assert img.size[0] > 0 and img.size[1] > 0

# 6. Audit Merge Traceability
def test_audit_merge_log_completeness(db_conn):
    cur = db_conn.cursor()
    cur.execute("SELECT COUNT(*) FROM audit_merge_log;")
    log_count = cur.fetchone()[0]
    assert log_count >= 1295, f"Expected at least 1,295 audit merge entries, got {log_count}"
    
    cur.execute("SELECT operation_type, COUNT(*) FROM audit_merge_log GROUP BY operation_type;")
    op_counts = dict(cur.fetchall())
    assert "MERGE_EXACT_DUPLICATE" in op_counts
    assert op_counts["MERGE_EXACT_DUPLICATE"] > 1100

# 7. Product Engine API Tests
def test_engine_supported_languages(engine):
    langs = engine.get_supported_languages()
    assert "uz_latn" in langs
    assert "uz_cyrl" in langs
    assert "ru" in langs

def test_engine_get_categories(engine):
    cats = engine.get_categories("uz_latn")
    assert len(cats) >= 5
    for c in cats:
        assert "category_id" in c
        assert "name" in c
        assert c["question_count"] > 0

def test_engine_exam_simulation_flow(engine):
    # Create 20-question exam session
    session = engine.create_exam_session(language="uz_latn")
    assert session["total_questions"] == 20
    assert len(session["questions"]) == 20
    assert session["time_limit_seconds"] == 1500 # 25 mins

    # Simulate answering
    answers_map = {}
    for q in session["questions"]:
        # check question structure
        assert q.canonical_id.startswith(("CANON-YHQ-", "CQ-"))
        assert len(q.options) >= 2
        # choose first option
        answers_map[q.canonical_id] = q.options[0].option_key

    # Evaluate
    result = engine.evaluate_test_session(
        session["session_id"], answers_map, language="uz_latn", time_elapsed_seconds=120.5
    )
    assert result.total_questions == 20
    assert result.correct_count + result.incorrect_count == 20
    assert result.passed == (result.correct_count >= 18)

    # Test mistake review session if any mistakes were made
    if result.incorrect_question_ids:
        rev = engine.create_mistakes_review_session(result.incorrect_question_ids, language="uz_latn")
        assert rev["total_questions"] == len(result.incorrect_question_ids)
