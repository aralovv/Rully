"""
Versioned Schema Migration Engine for SQLite & Turso (Phase 1D & Phase 1E).
Supports forward-only idempotent migrations using atomic execute_batch(),
strict DQS=0 single-quoted string literals, and read-only parity verification.
"""

from datetime import datetime
import hashlib
import json
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

from src.db.sqlite_utils import get_index_names, get_table_columns, list_user_tables
from src.db_adapter import execute_batch

SCHEMA_MIGRATIONS_DDL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    applied_at TEXT NOT NULL,
    checksum TEXT NOT NULL
)
"""

USER_TICKET_PROGRESS_DDL = """
CREATE TABLE IF NOT EXISTS user_ticket_progress (
    user_id INTEGER NOT NULL,
    ticket_number INTEGER NOT NULL,
    total_questions INTEGER NOT NULL DEFAULT 20,
    best_correct INTEGER NOT NULL DEFAULT 0,
    best_percentage REAL NOT NULL DEFAULT 0.0,
    attempts_count INTEGER NOT NULL DEFAULT 1,
    is_passed INTEGER NOT NULL DEFAULT 0,
    last_session_id TEXT,
    last_attempted_at TEXT NOT NULL,
    PRIMARY KEY (user_id, ticket_number),
    FOREIGN KEY (user_id) REFERENCES telegram_users(user_id) ON DELETE CASCADE
)
"""

EDITORIAL_REVIEW_QUEUE_DDL = """
CREATE TABLE IF NOT EXISTS editorial_review_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_id TEXT NOT NULL,
    language TEXT NOT NULL DEFAULT 'all',
    draft_question_text TEXT,
    draft_explanation TEXT,
    draft_legal_status TEXT NOT NULL DEFAULT 'UNRESOLVED_LEGAL_REVIEW',
    draft_legal_doc_title TEXT,
    draft_legal_doc_url TEXT,
    draft_legal_chapter TEXT,
    draft_legal_clause TEXT,
    source_type TEXT NOT NULL DEFAULT 'AUDIT_FLAG',
    review_status TEXT NOT NULL DEFAULT 'PENDING_EDITORIAL_REVIEW',
    issue_flags_json TEXT,
    created_by TEXT NOT NULL DEFAULT 'system_audit',
    created_at TEXT NOT NULL,
    reviewed_by TEXT,
    reviewed_at TEXT,
    reviewer_notes TEXT,
    FOREIGN KEY (canonical_id) REFERENCES canonical_questions(canonical_id) ON DELETE CASCADE
)
"""

REQUIRED_INDEXES: Dict[str, str] = {
    "idx_answers_session": "CREATE INDEX IF NOT EXISTS idx_answers_session ON session_answers(session_id)",
    "idx_exam_results_user": "CREATE INDEX IF NOT EXISTS idx_exam_results_user ON exam_results(user_id)",
    "idx_session_answers_user_canon": (
        "CREATE INDEX IF NOT EXISTS idx_session_answers_user_canon ON session_answers(user_id, canonical_id, is_correct)"
    ),
    "idx_session_answers_user_recent": (
        "CREATE INDEX IF NOT EXISTS idx_session_answers_user_recent ON session_answers(user_id, id DESC)"
    ),
    "idx_sessions_user_status": "CREATE INDEX IF NOT EXISTS idx_sessions_user_status ON user_sessions(user_id, status)",
    "idx_ticket_progress_user": "CREATE INDEX IF NOT EXISTS idx_ticket_progress_user ON user_ticket_progress(user_id)",
    "idx_ai_usage": "CREATE INDEX IF NOT EXISTS idx_ai_usage ON ai_usage_limits(user_id, usage_date)",
}

EDITORIAL_INDEXES: Dict[str, str] = {
    "idx_editorial_status": "CREATE INDEX IF NOT EXISTS idx_editorial_status ON editorial_review_queue(review_status)",
    "idx_editorial_canon": "CREATE INDEX IF NOT EXISTS idx_editorial_canon ON editorial_review_queue(canonical_id, language)",
}

USER_QUESTION_SRS_DDL = """
CREATE TABLE IF NOT EXISTS user_question_srs (
    user_id INTEGER NOT NULL,
    canonical_id TEXT NOT NULL,
    ease_factor REAL NOT NULL DEFAULT 2.5,
    interval_days INTEGER NOT NULL DEFAULT 0,
    repetitions INTEGER NOT NULL DEFAULT 0,
    lapses INTEGER NOT NULL DEFAULT 0,
    last_quality INTEGER NOT NULL DEFAULT 0,
    last_reviewed_at TEXT NOT NULL,
    next_review_at TEXT NOT NULL,
    prev_state_json TEXT DEFAULT NULL,
    PRIMARY KEY (user_id, canonical_id),
    FOREIGN KEY (user_id) REFERENCES telegram_users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (canonical_id) REFERENCES canonical_questions(canonical_id) ON DELETE CASCADE
)
"""

PHASE4_REMOVED_TABLES: Tuple[str, ...] = (
    "practical_checklist",
    "practical_quiz_results",
)

PHASE4_REMOVED_INDEXES: Tuple[str, ...] = (
    "idx_checklist_user",
    "idx_practical_quiz_user",
)

PHASE4_EXTRA_INDEXES: Dict[str, str] = {
    "idx_session_answers_user_answered": (
        "CREATE INDEX IF NOT EXISTS idx_session_answers_user_answered "
        "ON session_answers(user_id, is_correct, answered_at)"
    ),
}

SRS_INDEXES: Dict[str, str] = {
    "idx_srs_user_due": "CREATE INDEX IF NOT EXISTS idx_srs_user_due ON user_question_srs(user_id, next_review_at)",
    "idx_srs_user_reps": "CREATE INDEX IF NOT EXISTS idx_srs_user_reps ON user_question_srs(user_id, repetitions, lapses)",
}

VMQ_ARTICLES_DDL = """
CREATE TABLE IF NOT EXISTS vmq_articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_key TEXT UNIQUE NOT NULL,
    entry_type TEXT NOT NULL,
    chapter_code TEXT NOT NULL,
    chapter_num INTEGER NOT NULL,
    clause_num TEXT,
    clause_sort REAL NOT NULL DEFAULT 0.0,
    title_uz TEXT NOT NULL,
    title_ru TEXT NOT NULL,
    text_uz TEXT NOT NULL,
    text_ru TEXT NOT NULL,
    doc_url_uz TEXT NOT NULL,
    doc_url_ru TEXT NOT NULL,
    effective_date TEXT NOT NULL DEFAULT '2022-05-01',
    updated_at TEXT NOT NULL
)
"""

VMQ_INDEXES: Dict[str, str] = {
    "idx_vmq_chapter": "CREATE INDEX IF NOT EXISTS idx_vmq_chapter ON vmq_articles(chapter_code, clause_sort)",
    "idx_vmq_clause": "CREATE INDEX IF NOT EXISTS idx_vmq_clause ON vmq_articles(clause_num)",
}

PROVENANCE_COLUMNS: List[Tuple[str, str]] = [
    ("legal_verification_status", "TEXT NOT NULL DEFAULT 'UNRESOLVED_LEGAL_REVIEW'"),
    ("legal_doc_title", "TEXT DEFAULT NULL"),
    ("legal_doc_url", "TEXT DEFAULT NULL"),
    ("legal_chapter", "TEXT DEFAULT NULL"),
    ("legal_clause", "TEXT DEFAULT NULL"),
    ("legal_effective_date", "TEXT DEFAULT NULL"),
    ("editorial_reviewed_by", "TEXT DEFAULT NULL"),
    ("editorial_reviewed_at", "TEXT DEFAULT NULL"),
]


def _checksum(items: List[str]) -> str:
    return hashlib.sha256("\n".join(items).encode("utf-8")).hexdigest()[:16]


def _ensure_migrations_table(conn: Any) -> None:
    execute_batch(conn, [SCHEMA_MIGRATIONS_DDL.strip()])


def _record_migration_stmt(version: str, name: str, checksum: str) -> Tuple[str, List[Any]]:
    now_ts = datetime.utcnow().isoformat()
    return (
        """
        INSERT OR IGNORE INTO schema_migrations (version, name, applied_at, checksum)
        VALUES (?, ?, ?, ?)
        """,
        [version, name, now_ts, checksum],
    )


def apply_phase1_migrations(conn: Any) -> Dict[str, Any]:
    """
    Applies Phase 1D and Phase 1E migrations cleanly and idempotently on either
    SQLite or TursoConnection inside atomic execute_batch() transactions.
    """
    _ensure_migrations_table(conn)

    applied: List[str] = []
    # ---- Migration 001: session_answers.user_id, user_ticket_progress, 6+1 indexes ----
    sa_cols = get_table_columns(conn, "session_answers")
    existing_tables = set(list_user_tables(conn))
    existing_indexes = get_index_names(conn)

    # Step 1a: Schema DDL first so remote Turso Hrana prepares subsequent DML/indexes safely
    ddl_001: List[Any] = []
    if "user_id" not in sa_cols:
        ddl_001.append("ALTER TABLE session_answers ADD COLUMN user_id INTEGER DEFAULT NULL")
    if "user_ticket_progress" not in existing_tables:
        ddl_001.append(USER_TICKET_PROGRESS_DDL.strip())
    if ddl_001:
        execute_batch(conn, ddl_001)

    # Step 1b: Backfill session_answers.user_id, add indexes, record migration
    dml_idx_001: List[Any] = [
        """
        UPDATE session_answers
        SET user_id = (
            SELECT us.user_id
            FROM user_sessions us
            WHERE us.session_id = session_answers.session_id
        )
        WHERE user_id IS NULL
        """.strip()
    ]
    existing_indexes = get_index_names(conn)
    for idx_name, idx_sql in REQUIRED_INDEXES.items():
        if idx_name not in existing_indexes:
            dml_idx_001.append(idx_sql)
    dml_idx_001.append(
        _record_migration_stmt(
            "001_phase1d_session_answers_and_ticket_progress",
            "Add session_answers.user_id + backfill, user_ticket_progress, and 7 missing indexes",
            _checksum([USER_TICKET_PROGRESS_DDL] + list(REQUIRED_INDEXES.values())),
        )
    )
    execute_batch(conn, dml_idx_001)
    applied.append("001_phase1d_session_answers_and_ticket_progress")

    # ---- Migration 002: Classified Provenance & Editorial Review Queue ----
    cq_cols = get_table_columns(conn, "canonical_questions")
    existing_tables = set(list_user_tables(conn))

    ddl_002: List[Any] = []
    for col_name, col_def in PROVENANCE_COLUMNS:
        if col_name not in cq_cols:
            ddl_002.append(f"ALTER TABLE canonical_questions ADD COLUMN {col_name} {col_def}")
    if "editorial_review_queue" not in existing_tables:
        ddl_002.append(EDITORIAL_REVIEW_QUEUE_DDL.strip())
    if ddl_002:
        execute_batch(conn, ddl_002)

    existing_indexes = get_index_names(conn)
    idx_002: List[Any] = []
    for idx_name, idx_sql in EDITORIAL_INDEXES.items():
        if idx_name not in existing_indexes:
            idx_002.append(idx_sql)
    idx_002.append(
        _record_migration_stmt(
            "002_phase1e_classified_provenance_and_editorial_queue",
            "Add Classified Provenance columns to canonical_questions and create editorial_review_queue",
            _checksum([EDITORIAL_REVIEW_QUEUE_DDL] + [f"{c}:{d}" for c, d in PROVENANCE_COLUMNS]),
        )
    )
    execute_batch(conn, idx_002)
    applied.append("002_phase1e_classified_provenance_and_editorial_queue")

    return {"applied_migrations": applied, "parity": verify_schema_parity(conn)}


def verify_schema_parity(conn: Any) -> Dict[str, Any]:
    """Verifies tables, columns, indexes, backfill completeness, and FK zero-orphan status."""
    tables = set(list_user_tables(conn))
    indexes = get_index_names(conn)
    sa_cols = get_table_columns(conn, "session_answers") if "session_answers" in tables else set()
    cq_cols = get_table_columns(conn, "canonical_questions") if "canonical_questions" in tables else set()

    expected_tables = {"user_ticket_progress", "editorial_review_queue", "schema_migrations"}
    missing_tables = sorted(expected_tables - tables)
    all_req_indexes = set(REQUIRED_INDEXES.keys()) | set(EDITORIAL_INDEXES.keys())
    missing_indexes = sorted(all_req_indexes - indexes)
    missing_sa_cols = sorted({"user_id"} - sa_cols)
    missing_cq_cols = sorted({c for c, _ in PROVENANCE_COLUMNS} - cq_cols)

    cur = conn.cursor()
    if "user_id" in sa_cols:
        cur.execute("SELECT COUNT(*) FROM session_answers WHERE user_id IS NULL")
        r_null = cur.fetchone()
        null_sa_uid = r_null[0] if not hasattr(r_null, "values") else list(r_null.values())[0]
    else:
        null_sa_uid = -1

    # Check FK anti-joins safely via SELECT (skipping tables not yet migrated / rolled back)
    orphan_checks = [
        (
            "session_answers.session_id",
            {"session_answers", "user_sessions"},
            "SELECT COUNT(*) FROM session_answers sa LEFT JOIN user_sessions us "
            "ON sa.session_id = us.session_id WHERE us.session_id IS NULL",
        ),
        (
            "session_answers.canonical_id",
            {"session_answers", "canonical_questions"},
            "SELECT COUNT(*) FROM session_answers sa LEFT JOIN canonical_questions cq "
            "ON sa.canonical_id = cq.canonical_id WHERE cq.canonical_id IS NULL",
        ),
        (
            "user_ticket_progress.user_id",
            {"user_ticket_progress", "telegram_users"},
            "SELECT COUNT(*) FROM user_ticket_progress tp LEFT JOIN telegram_users tu "
            "ON tp.user_id = tu.user_id WHERE tu.user_id IS NULL",
        ),
        (
            "editorial_review_queue.canonical_id",
            {"editorial_review_queue", "canonical_questions"},
            "SELECT COUNT(*) FROM editorial_review_queue eq LEFT JOIN canonical_questions cq "
            "ON eq.canonical_id = cq.canonical_id WHERE cq.canonical_id IS NULL",
        ),
    ]
    orphans = {}
    for label, req_tables, sql in orphan_checks:
        if not req_tables.issubset(tables):
            continue
        cur.execute(sql)
        row = cur.fetchone()
        cnt = row[0] if not hasattr(row, "values") else list(row.values())[0]
        if cnt > 0:
            orphans[label] = cnt

    passed = (
        not missing_tables
        and not missing_indexes
        and not missing_sa_cols
        and not missing_cq_cols
        and null_sa_uid == 0
        and not orphans
    )
    return {
        "passed": passed,
        "missing_tables": missing_tables,
        "missing_indexes": missing_indexes,
        "missing_session_answers_columns": missing_sa_cols,
        "missing_canonical_columns": missing_cq_cols,
        "null_session_answers_user_id": null_sa_uid,
        "fk_orphans": orphans,
    }


def rollback_phase1_migrations_local_test(conn: sqlite3.Connection) -> Dict[str, Any]:
    """
    Isolated rollback helper used ONLY to test clean schema rollback on staging/test SQLite copies.
    Removes Phase 1D/1E added indexes/tables/columns cleanly while preserving existing pre-1D user data.
    """
    stmts: List[str] = []
    for idx_name in list(EDITORIAL_INDEXES.keys()) + list(REQUIRED_INDEXES.keys()):
        stmts.append(f"DROP INDEX IF EXISTS {idx_name}")
    stmts.append("DROP TABLE IF EXISTS editorial_review_queue")
    stmts.append("DROP TABLE IF EXISTS user_ticket_progress")

    cq_cols = get_table_columns(conn, "canonical_questions")
    for col_name, _ in reversed(PROVENANCE_COLUMNS):
        if col_name in cq_cols:
            stmts.append(f"ALTER TABLE canonical_questions DROP COLUMN {col_name}")

    sa_cols = get_table_columns(conn, "session_answers")
    if "user_id" in sa_cols:
        for idx_name in PHASE4_EXTRA_INDEXES.keys():
            stmts.append(f"DROP INDEX IF EXISTS {idx_name}")
        stmts.append("ALTER TABLE session_answers DROP COLUMN user_id")

    stmts.append("DROP TABLE IF EXISTS schema_migrations")
    execute_batch(conn, stmts)
    return {"rolled_back": True, "tables_remaining": list_user_tables(conn)}


def apply_phase5_migrations(conn: Any) -> Dict[str, Any]:
    """
    Applies Phase 5 SM-2 Spaced Repetition schema migration (`003_phase5_user_question_srs`)
    idempotently across SQLite and remote Turso using DDL-before-index batching.
    """
    _ensure_migrations_table(conn)
    existing_tables = set(list_user_tables(conn))

    if "user_question_srs" not in existing_tables:
        execute_batch(conn, [USER_QUESTION_SRS_DDL.strip()])

    existing_indexes = get_index_names(conn)
    idx_003: List[Any] = []
    for idx_name, idx_sql in SRS_INDEXES.items():
        if idx_name not in existing_indexes:
            idx_003.append(idx_sql)
    idx_003.append(
        _record_migration_stmt(
            "003_phase5_user_question_srs",
            "Create user_question_srs SM-2 spaced repetition table and due-queue indexes",
            _checksum([USER_QUESTION_SRS_DDL] + list(SRS_INDEXES.values())),
        )
    )
    execute_batch(conn, idx_003)

    return {
        "applied_migrations": ["003_phase5_user_question_srs"],
        "parity": verify_phase5_schema_parity(conn),
    }


def apply_phase3_migrations(conn: Any) -> Dict[str, Any]:
    """
    Applies Phase 3 Authoritative VMQ 172 Statutory Corpus table migration (`004_phase3_vmq_articles`)
    idempotently across SQLite and remote Turso using DDL-before-index batching.
    """
    _ensure_migrations_table(conn)
    existing_tables = set(list_user_tables(conn))

    if "vmq_articles" not in existing_tables:
        execute_batch(conn, [VMQ_ARTICLES_DDL.strip()])

    existing_indexes = get_index_names(conn)
    idx_004: List[Any] = []
    for idx_name, idx_sql in VMQ_INDEXES.items():
        if idx_name not in existing_indexes:
            idx_004.append(idx_sql)
    idx_004.append(
        _record_migration_stmt(
            "004_phase3_vmq_articles",
            "Create vmq_articles statutory VMQ 172 bilingual law corpus table and lookup indexes",
            _checksum([VMQ_ARTICLES_DDL] + list(VMQ_INDEXES.values())),
        )
    )
    execute_batch(conn, idx_004)

    return {
        "applied_migrations": ["004_phase3_vmq_articles"],
        "parity": verify_phase3_schema_parity(conn),
    }


def apply_phase4_migrations(conn: Any) -> Dict[str, Any]:
    """
    Applies Phase 4 Architecture, DB-backed SM-2 undo state (`prev_state_json`),
    indexed student answer lookups, and Workstream 4C table cleanup (`005_phase4_architecture`).
    Strictly preserves all live user, payment, exam, session, and SRS data.
    """
    _ensure_migrations_table(conn)
    existing_tables = set(list_user_tables(conn))
    existing_indexes = get_index_names(conn)

    # 1. DDL additions first
    ddl_005: List[Any] = []
    if "user_question_srs" in existing_tables:
        srs_cols = get_table_columns(conn, "user_question_srs")
        if "prev_state_json" not in srs_cols:
            ddl_005.append("ALTER TABLE user_question_srs ADD COLUMN prev_state_json TEXT DEFAULT NULL")
    if ddl_005:
        execute_batch(conn, ddl_005)

    # 2. Drop deprecated 4C practical checklist / situational scenario tables & indexes + add 4A indexes
    batch_005: List[Any] = []
    for idx_name in PHASE4_REMOVED_INDEXES:
        if idx_name in existing_indexes:
            batch_005.append(f"DROP INDEX IF EXISTS {idx_name}")
    for tbl_name in PHASE4_REMOVED_TABLES:
        if tbl_name in existing_tables:
            batch_005.append(f"DROP TABLE IF EXISTS {tbl_name}")
    if "session_answers" in existing_tables:
        sa_cols = get_table_columns(conn, "session_answers")
        if "user_id" in sa_cols:
            for idx_name, idx_sql in PHASE4_EXTRA_INDEXES.items():
                if idx_name not in existing_indexes:
                    batch_005.append(idx_sql)
    batch_005.append(
        _record_migration_stmt(
            "005_phase4_architecture",
            "Persist prev_state_json in user_question_srs, add Phase 4 analytics index, drop removed checklist/scenario tables",
            _checksum(list(PHASE4_REMOVED_TABLES) + list(PHASE4_EXTRA_INDEXES.values()) + ["prev_state_json"]),
        )
    )
    execute_batch(conn, batch_005)

    return {
        "applied_migrations": ["005_phase4_architecture"],
        "parity": verify_phase4_schema_parity(conn),
    }


def verify_phase4_schema_parity(conn: Any) -> Dict[str, Any]:
    """Verifies Phase 4 schema changes: prev_state_json present, 4C tables/indexes dropped, extra index present."""
    tables = set(list_user_tables(conn))
    indexes = get_index_names(conn)
    srs_cols = get_table_columns(conn, "user_question_srs") if "user_question_srs" in tables else set()

    missing_cols = sorted({"prev_state_json"} - srs_cols)
    stray_tables = sorted(set(PHASE4_REMOVED_TABLES) & tables)
    stray_indexes = sorted(set(PHASE4_REMOVED_INDEXES) & indexes)
    missing_indexes = sorted(set(PHASE4_EXTRA_INDEXES.keys()) - indexes)

    passed = not missing_cols and not stray_tables and not stray_indexes and not missing_indexes
    return {
        "passed": passed,
        "missing_srs_columns": missing_cols,
        "stray_removed_tables": stray_tables,
        "stray_removed_indexes": stray_indexes,
        "missing_indexes": missing_indexes,
    }


def verify_phase3_schema_parity(conn: Any) -> Dict[str, Any]:
    """Verifies Phase 3 vmq_articles table, required columns, and lookup indexes."""
    tables = set(list_user_tables(conn))
    indexes = get_index_names(conn)
    vmq_cols = get_table_columns(conn, "vmq_articles") if "vmq_articles" in tables else set()

    expected_cols = {
        "id",
        "article_key",
        "entry_type",
        "chapter_code",
        "chapter_num",
        "clause_num",
        "clause_sort",
        "title_uz",
        "title_ru",
        "text_uz",
        "text_ru",
        "doc_url_uz",
        "doc_url_ru",
        "effective_date",
        "updated_at",
    }
    missing_tables = sorted({"vmq_articles", "schema_migrations"} - tables)
    missing_indexes = sorted(set(VMQ_INDEXES.keys()) - indexes)
    missing_cols = sorted(expected_cols - vmq_cols)
    passed = not missing_tables and not missing_indexes and not missing_cols
    return {
        "passed": passed,
        "missing_tables": missing_tables,
        "missing_indexes": missing_indexes,
        "missing_vmq_columns": missing_cols,
    }


def apply_all_migrations(conn: Any) -> Dict[str, Any]:
    """Applies Phase 1 (001, 002), Phase 5 (003), Phase 3 (004), and Phase 4 (005) migrations idempotently."""
    p1 = apply_phase1_migrations(conn)
    p5 = apply_phase5_migrations(conn)
    p3 = apply_phase3_migrations(conn)
    p4 = apply_phase4_migrations(conn)
    combined_passed = bool(
        p1["parity"]["passed"]
        and p5["parity"]["passed"]
        and p3["parity"]["passed"]
        and p4["parity"]["passed"]
    )
    return {
        "applied_migrations": (
            p1["applied_migrations"]
            + p5["applied_migrations"]
            + p3["applied_migrations"]
            + p4["applied_migrations"]
        ),
        "parity": {
            "passed": combined_passed,
            "phase1": p1["parity"],
            "phase5": p5["parity"],
            "phase3": p3["parity"],
            "phase4": p4["parity"],
        },
    }


def verify_phase5_schema_parity(conn: Any) -> Dict[str, Any]:
    """Verifies Phase 5 user_question_srs table, columns, indexes, and zero FK orphans."""
    tables = set(list_user_tables(conn))
    indexes = get_index_names(conn)
    srs_cols = get_table_columns(conn, "user_question_srs") if "user_question_srs" in tables else set()

    expected_cols = {
        "user_id",
        "canonical_id",
        "ease_factor",
        "interval_days",
        "repetitions",
        "lapses",
        "last_quality",
        "last_reviewed_at",
        "next_review_at",
    }
    missing_tables = sorted({"user_question_srs", "schema_migrations"} - tables)
    missing_indexes = sorted(set(SRS_INDEXES.keys()) - indexes)
    missing_cols = sorted(expected_cols - srs_cols)

    orphans: Dict[str, int] = {}
    if "user_question_srs" in tables:
        cur = conn.cursor()
        orphan_checks = {
            "user_question_srs.user_id": (
                "SELECT COUNT(*) FROM user_question_srs s LEFT JOIN telegram_users tu "
                "ON s.user_id = tu.user_id WHERE tu.user_id IS NULL"
            ),
            "user_question_srs.canonical_id": (
                "SELECT COUNT(*) FROM user_question_srs s LEFT JOIN canonical_questions cq "
                "ON s.canonical_id = cq.canonical_id WHERE cq.canonical_id IS NULL"
            ),
        }
        for label, sql in orphan_checks.items():
            cur.execute(sql)
            row = cur.fetchone()
            cnt = row[0] if not hasattr(row, "values") else list(row.values())[0]
            if cnt > 0:
                orphans[label] = cnt

    passed = not missing_tables and not missing_indexes and not missing_cols and not orphans
    return {
        "passed": passed,
        "missing_tables": missing_tables,
        "missing_indexes": missing_indexes,
        "missing_srs_columns": missing_cols,
        "fk_orphans": orphans,
    }


def rollback_phase5_migrations_local_test(conn: sqlite3.Connection) -> Dict[str, Any]:
    """Removes Phase 5 SRS schema artifacts cleanly for isolated staging rollback drills."""
    stmts: List[Any] = [f"DROP INDEX IF EXISTS {idx_name}" for idx_name in SRS_INDEXES.keys()]
    stmts.append("DROP TABLE IF EXISTS user_question_srs")
    stmts.append(("DELETE FROM schema_migrations WHERE version = ?", ["003_phase5_user_question_srs"]))
    execute_batch(conn, stmts)
    return {"rolled_back": True, "tables_remaining": list_user_tables(conn)}
