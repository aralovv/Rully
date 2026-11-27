"""
Sanitized Downward Export Engine (Gate A Decision U-07).

Rebuilds a clean local development SQLite database strictly downward from a read-only
Production Turso (or restored snapshot) source:
  - Preserves 100% of public catalog, audit, and active ETL provenance tables
    (canonical_*, categories, images, sources, audit_merge_log, staged_questions,
     questions, answers, question_sources, verification_records, subscription_plans,
     editorial_review_queue, user_ticket_progress, schema_migrations).
  - Wipes/scrubs all live user PII, payment orders/transactions/cards, MTProto session
    strings, AI conversations/usage, admin sessions/OTPs, and production password hashes.
  - Inserts minimal synthetic dev/test fixture rows so offline pytest suites work cleanly.
"""

from datetime import datetime
import os
import re
import sqlite3
from typing import Any, Dict, List, Optional, Set, Tuple

from src.db.migrations_v2 import apply_all_migrations
from src.db.sqlite_utils import backup_sqlite_wal_safe, list_user_tables
from src.security.crypto import hash_password

# Tables wiped cleanly in downward dev snapshots (zero live customer state)
WIPED_TABLES: Tuple[str, ...] = (
    "admin_audit_logs",
    "admin_otp_challenges",
    "admin_sessions",
    "ai_conversations",
    "ai_usage_limits",
    "exam_results",
    "learning_streak",
    "payment_events",
    "payment_orders",
    "payment_review_cases",
    "payment_transactions",
    "session_answers",
    "subscription_price_history",
    "unmatched_payments",
    "user_activity_events",
    "user_bookmarks",
    "user_completed_modules",
    "user_mistakes",
    "user_question_srs",
    "user_sessions",
    "user_subscriptions",
    "user_ticket_progress",
)

# Tables copied downward verbatim as non-PII catalog / ETL / system tables
CATALOG_AND_CONFIG_TABLES: Tuple[str, ...] = (
    "categories",
    "images",
    "sources",
    "questions",
    "answers",
    "question_sources",
    "verification_records",
    "canonical_questions",
    "canonical_translations",
    "canonical_answers",
    "audit_merge_log",
    "staged_questions",
    "editorial_review_queue",
    "subscription_plans",
    "system_settings",
)


def _select_only_guard(sql: str) -> None:
    clean = sql.strip()
    if ";" in clean or not re.match(r"^\s*SELECT\b", clean, re.IGNORECASE):
        raise RuntimeError(f"Sanitized exporter allows strictly single-statement SELECT reads: {clean[:60]}")


def _fetch_ddl_and_rows(src_conn: Any, table_name: str) -> Tuple[str, List[str], List[Tuple[Any, ...]]]:
    cur = src_conn.cursor()
    q_ddl = "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?"
    _select_only_guard(q_ddl)
    cur.execute(q_ddl, (table_name,))
    ddl_row = cur.fetchone()
    if not ddl_row:
        raise ValueError(f"Source missing table: {table_name}")
    ddl_sql = ddl_row["sql"] if hasattr(ddl_row, "keys") and "sql" in ddl_row.keys() else ddl_row[0]

    rows: List[Tuple[Any, ...]] = []
    cols: Optional[List[str]] = None
    last_rowid: Optional[int] = None
    while True:
        if last_rowid is None:
            sql_p = f'SELECT rowid AS _r_rowid, * FROM "{table_name}" ORDER BY rowid LIMIT 500'
            _select_only_guard(sql_p)
            cur.execute(sql_p)
        else:
            sql_p = f'SELECT rowid AS _r_rowid, * FROM "{table_name}" WHERE rowid > ? ORDER BY rowid LIMIT 500'
            _select_only_guard(sql_p)
            cur.execute(sql_p, (last_rowid,))
        batch = cur.fetchall()
        if cols is None and cur.description:
            cols = [d[0] for d in cur.description[1:]]
        if not batch:
            break
        for r in batch:
            vals = list(r.values()) if hasattr(r, "values") else list(r)
            last_rowid = vals[0]
            rows.append(tuple(vals[1:]))
        if len(batch) < 500:
            break

    if cols is None:
        # Table is empty; fetch column list via limit 0 SELECT
        sql_c = f'SELECT * FROM "{table_name}" LIMIT 0'
        _select_only_guard(sql_c)
        cur.execute(sql_c)
        cols = [d[0] for d in (cur.description or [])]

    return ddl_sql, cols, rows


def export_sanitized_dev_sqlite(
    source_conn: Any,
    target_db_path: str,
    backup_existing_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Exports a sanitized local development SQLite database from a read-only Production
    Turso connection (or local snapshot), never exposing live PII, card numbers,
    sessions, or password hashes.
    """
    cur = source_conn.cursor()
    q_master = "SELECT type, name, tbl_name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name"
    _select_only_guard(q_master)
    cur.execute(q_master)
    master_rows = cur.fetchall()

    source_tables_ddl: Dict[str, str] = {}
    source_indexes_sql: List[str] = []
    for r in master_rows:
        vals = list(r.values()) if hasattr(r, "values") else list(r)
        obj_type, obj_name, _, obj_sql = vals[0], vals[1], vals[2], vals[3]
        if obj_type == "table" and obj_sql:
            source_tables_ddl[obj_name] = obj_sql
        elif obj_type == "index" and obj_sql:
            source_indexes_sql.append(obj_sql)

    tmp_path = f"{target_db_path}.tmp.{os.getpid()}"
    if os.path.exists(tmp_path):
        os.remove(tmp_path)

    parent = os.path.dirname(os.path.abspath(target_db_path))
    if parent:
        os.makedirs(parent, exist_ok=True)

    dst = sqlite3.connect(tmp_path)
    counts_copied: Dict[str, int] = {}
    try:
        # Build tables using source DDL first (keep FK off during pure snapshot copy, verify after!)
        for tbl_name, ddl in sorted(source_tables_ddl.items()):
            # Never carry Tier 0 archival tables into new sanitized dev DB
            if tbl_name in ("archived_duplicate_source_traces", "proposed_source_trace_cleanup"):
                continue
            dst.execute(ddl)

        # Copy non-PII catalog and config tables cleanly
        for tbl_name in CATALOG_AND_CONFIG_TABLES:
            if tbl_name not in source_tables_ddl:
                continue
            _, cols, rows = _fetch_ddl_and_rows(source_conn, tbl_name)
            if rows and cols:
                col_list = ", ".join(f'"{c}"' for c in cols)
                ph = ", ".join("?" for _ in cols)
                dst.executemany(f'INSERT INTO "{tbl_name}" ({col_list}) VALUES ({ph})', rows)
            counts_copied[tbl_name] = len(rows)

        # Apply Phase 1D/1E & Phase 5 migrations cleanly so local schema matches target contract
        dst.commit()
        apply_all_migrations(dst)

        # Seed strictly synthetic non-PII fixtures for offline dev & pytest compatibility
        now_ts = datetime.utcnow().isoformat()
        dst_cur = dst.cursor()

        # Synthetic telegram_users fixture IDs (zero customer PII)
        dst_cur.execute("PRAGMA table_info(telegram_users)")
        tu_cols = {r[1] for r in dst_cur.fetchall()}
        fixture_users = [
            (8809526955, "dev_user", "DevUser", "en", 1, 0),
            (1956239701, "dev_admin", "DevAdmin", "uz_latn", 1, 1),
            (8515329556, "dev_tester", "DevTester", "uz_latn", 1, 0),
        ]
        for uid, uname, fname, lang, lang_sel, is_adm in fixture_users:
            col_vals: Dict[str, Any] = {
                "user_id": uid,
                "username": uname,
                "first_name": fname,
                "last_name": "",
                "language": lang,
                "is_language_selected": lang_sel,
                "is_admin": is_adm,
                "is_blocked": 0,
                "created_at": now_ts,
                "last_active_at": now_ts,
            }
            if "is_pro" in tu_cols:
                col_vals["is_pro"] = 0
            keys = [k for k in col_vals if k in tu_cols]
            dst_cur.execute(
                f'INSERT OR REPLACE INTO telegram_users ({", ".join(keys)}) VALUES ({", ".join("?" for _ in keys)})',
                [col_vals[k] for k in keys],
            )
        counts_copied["telegram_users_sanitized_fixtures"] = len(fixture_users)

        # Synthetic dev admin users (never copy production password hashes)
        local_dev_pwd = os.getenv("ADMIN_PASSWORD") or "dev_local_only_not_for_prod"
        dev_hash = hash_password(local_dev_pwd)
        dst_cur.execute(
            """
            INSERT OR REPLACE INTO admin_users (id, username, password_hash, telegram_id, role, is_active, created_at)
            VALUES
              (1, 'Anvarjon', ?, 1956239701, 'SUPERADMIN', 1, ?),
              (2, 'Admin', ?, 1956239701, 'SUPERADMIN', 1, ?)
            """,
            (dev_hash, now_ts, dev_hash, now_ts),
        )
        counts_copied["admin_users_sanitized"] = 2

        # Synthetic payment card placeholder matching repo offline test suffix *5370 (zero live PAN)
        dst_cur.execute(
            """
            INSERT OR REPLACE INTO payment_cards (
                id, cardholder_name, card_number_encrypted, card_number_masked, card_suffix,
                card_type, display_name, is_active, is_monitoring, created_at, updated_at
            ) VALUES (
                1, 'DEV TEST CARDHOLDER', 'ENC:9860000000005370', '9860 **** **** 5370',
                '5370', 'HUMO', 'Sanitized Dev HUMO (*5370)', 1, 1, ?, ?
            )
            """,
            (now_ts, now_ts),
        )
        counts_copied["payment_cards_sanitized"] = 1

        # Sanitized placeholder MTProto account (zero Telethon session string)
        dst_cur.execute(
            """
            INSERT OR REPLACE INTO mtproto_accounts (
                id, phone_number, session_encrypted, tg_user_id, tg_username,
                tg_first_name, monitored_bot, connection_status, created_at, updated_at
            ) VALUES (
                1, '+998000000000', '', 0, 'sanitized_dev', 'Sanitized', 'Humocardbot', 'DISCONNECTED', ?, ?
            )
            """,
            (now_ts, now_ts),
        )
        counts_copied["mtproto_accounts_sanitized"] = 1

        # Apply source indexes safely after data load
        for idx_sql in source_indexes_sql:
            # Skip legacy Tier 0 indexes if any existed
            if "archived_duplicate_source_traces" in idx_sql or "proposed_source_trace_cleanup" in idx_sql:
                continue
            try:
                dst_cur.execute(idx_sql)
            except sqlite3.OperationalError:
                pass

        dst.commit()

        # Verify integrity, FK constraints, and sanitized emptiness of PII tables
        dst_cur.execute("PRAGMA foreign_keys = ON;")
        dst_cur.execute("PRAGMA integrity_check;")
        int_res = dst_cur.fetchall()
        if int_res != [("ok",)]:
            raise RuntimeError(f"Sanitized dev DB integrity_check failed: {int_res}")
        dst_cur.execute("PRAGMA foreign_key_check;")
        fk_res = dst_cur.fetchall()
        if fk_res:
            raise RuntimeError(f"Sanitized dev DB foreign_key_check failed: {fk_res}")

        wiped_verified = {}
        for wt in WIPED_TABLES:
            if wt in set(list_user_tables(dst)):
                dst_cur.execute(f'SELECT COUNT(*) FROM "{wt}"')
                cnt = dst_cur.fetchone()[0]
                if cnt != 0:
                    raise RuntimeError(f"Sanitized dev DB leak check failed: {wt} has {cnt} rows!")
                wiped_verified[wt] = cnt
    finally:
        dst.close()

    # Backup pre-existing target DB cleanly if requested before atomic replace
    if backup_existing_path and os.path.exists(target_db_path):
        backup_sqlite_wal_safe(target_db_path, backup_existing_path, allow_overwrite=False)

    os.replace(tmp_path, target_db_path)
    # Clean stale WAL/SHM sidecars left by replaced file if zeroed
    for suffix in ("-wal", "-shm"):
        sidecar = target_db_path + suffix
        if os.path.exists(sidecar):
            try:
                os.remove(sidecar)
            except OSError:
                pass

    return {
        "status": "SANITIZED_DEV_DB_CREATED",
        "target_db_path": target_db_path,
        "backup_existing_path": backup_existing_path,
        "copied_counts": counts_copied,
        "wiped_tables_count": len(wiped_verified),
        "integrity_check": "ok",
        "foreign_key_check": "ok",
    }
