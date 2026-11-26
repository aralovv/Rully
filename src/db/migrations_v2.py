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
    cur.execute("SELECT COUNT(*) FROM session_answers WHERE user_id IS NULL")
    r_null = cur.fetchone()
    null_sa_uid = r_null[0] if not hasattr(r_null, "values") else list(r_null.values())[0]

    # Check FK anti-joins safely via SELECT
    orphan_checks = {
        "session_answers.session_id": (
            "SELECT COUNT(*) FROM session_answers sa LEFT JOIN user_sessions us "
            "ON sa.session_id = us.session_id WHERE us.session_id IS NULL"
        ),
        "session_answers.canonical_id": (
            "SELECT COUNT(*) FROM session_answers sa LEFT JOIN canonical_questions cq "
            "ON sa.canonical_id = cq.canonical_id WHERE cq.canonical_id IS NULL"
        ),
        "user_ticket_progress.user_id": (
            "SELECT COUNT(*) FROM user_ticket_progress tp LEFT JOIN telegram_users tu "
            "ON tp.user_id = tu.user_id WHERE tu.user_id IS NULL"
        ),
        "editorial_review_queue.canonical_id": (
            "SELECT COUNT(*) FROM editorial_review_queue eq LEFT JOIN canonical_questions cq "
            "ON eq.canonical_id = cq.canonical_id WHERE cq.canonical_id IS NULL"
        ),
    }
    orphans = {}
    for label, sql in orphan_checks.items():
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
        stmts.append("ALTER TABLE session_answers DROP COLUMN user_id")

    stmts.append("DROP TABLE IF EXISTS schema_migrations")
    execute_batch(conn, stmts)
    return {"rolled_back": True, "tables_remaining": list_user_tables(conn)}
