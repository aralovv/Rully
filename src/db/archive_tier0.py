"""
Tier 0 Archive Separation Engine (Gate A Decision U-01).
Extracts ONLY orphan historical snapshot tables:
  - archived_duplicate_source_traces
  - proposed_source_trace_cleanup
Leaves active ETL and sync dependencies (questions, answers, verification_records,
question_sources, sources, audit_merge_log, staged_questions) completely untouched.
"""

from datetime import datetime
import json
import os
import sqlite3
from typing import Any, Dict, List, Optional, Sequence, Tuple

from src.db.sqlite_utils import (
    compute_rows_sha256,
    list_user_tables,
    sql_literal,
)
from src.db_adapter import execute_batch

TIER0_TABLES: Tuple[str, ...] = (
    "archived_duplicate_source_traces",
    "proposed_source_trace_cleanup",
)


def verify_tier0_isolation_sqlite(runtime_conn: sqlite3.Connection) -> Dict[str, Any]:
    """Proves Tier 0 tables have zero incoming or outgoing FKs before extraction."""
    tables = list_user_tables(runtime_conn)
    incoming: List[Dict[str, Any]] = []
    outgoing: List[Dict[str, Any]] = []
    cur = runtime_conn.cursor()

    for tbl in tables:
        cur.execute(f'PRAGMA foreign_key_list("{tbl}")')
        for r in cur.fetchall():
            target = r["table"] if hasattr(r, "keys") and "table" in r.keys() else r[2]
            if tbl in TIER0_TABLES:
                outgoing.append({"table": tbl, "references": target})
            if target in TIER0_TABLES:
                incoming.append({"child_table": tbl, "references": target})

    present = [t for t in TIER0_TABLES if t in tables]
    return {
        "present_tables": present,
        "incoming_fks": incoming,
        "outgoing_fks": outgoing,
        "isolated": (len(incoming) == 0 and len(outgoing) == 0),
    }


def _fetch_table_snapshot(conn: Any, table_name: str) -> Dict[str, Any]:
    cur = conn.cursor()
    cur.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    )
    ddl_row = cur.fetchone()
    if not ddl_row:
        raise ValueError(f"Table '{table_name}' does not exist in source database.")
    ddl_sql = ddl_row["sql"] if hasattr(ddl_row, "keys") and "sql" in ddl_row.keys() else ddl_row[0]

    # Paginate cleanly via rowid for remote Turso compatibility as well as local SQLite
    rows: List[Tuple[Any, ...]] = []
    cols: Optional[List[str]] = None
    last_rowid: Optional[int] = None
    while True:
        if last_rowid is None:
            cur.execute(f'SELECT rowid AS _r_rowid, * FROM "{table_name}" ORDER BY rowid LIMIT 500')
        else:
            cur.execute(
                f'SELECT rowid AS _r_rowid, * FROM "{table_name}" WHERE rowid > ? ORDER BY rowid LIMIT 500',
                (last_rowid,),
            )
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
        cur.execute(f'PRAGMA table_info("{table_name}")')
        cols = [r["name"] if hasattr(r, "keys") and "name" in r.keys() else r[1] for r in cur.fetchall()]

    return {
        "table": table_name,
        "ddl": ddl_sql,
        "columns": cols,
        "rows": rows,
        "row_count": len(rows),
        "sha256": compute_rows_sha256(rows),
    }


def extract_tier0_from_connection(
    runtime_conn: Any,
    archive_db_path: str,
    drop_from_runtime: bool = False,
    dry_run: bool = False,
    source_label: str = "sqlite",
) -> Dict[str, Any]:
    """
    Safely copies Tier 0 orphan snapshot tables into archive_db_path, verifies
    exact row-count + SHA-256 parity in archive_db_path, and only optionally drops
    them from runtime_conn once verified.
    """
    existing_tables = set(list_user_tables(runtime_conn))
    targets = [t for t in TIER0_TABLES if t in existing_tables]
    if not targets:
        return {
            "status": "ALREADY_ARCHIVED",
            "source_label": source_label,
            "targets_found": [],
            "dropped": False,
        }

    # Verify zero FK links cleanly first
    if isinstance(runtime_conn, sqlite3.Connection):
        iso = verify_tier0_isolation_sqlite(runtime_conn)
        if not iso["isolated"]:
            raise RuntimeError(f"Tier 0 FK isolation check failed: {iso}")

    snapshots = {t: _fetch_table_snapshot(runtime_conn, t) for t in targets}

    if dry_run:
        return {
            "status": "DRY_RUN",
            "source_label": source_label,
            "targets": {t: {"rows": s["row_count"], "sha256": s["sha256"]} for t, s in snapshots.items()},
            "dropped": False,
        }

    arch_dir = os.path.dirname(os.path.abspath(archive_db_path))
    if arch_dir:
        os.makedirs(arch_dir, exist_ok=True)

    arch_conn = sqlite3.connect(archive_db_path)
    try:
        arch_cur = arch_conn.cursor()
        arch_cur.execute("""
            CREATE TABLE IF NOT EXISTS _tier0_archive_manifest (
                table_name TEXT PRIMARY KEY,
                source_label TEXT NOT NULL,
                row_count INTEGER NOT NULL,
                rows_sha256 TEXT NOT NULL,
                archived_at TEXT NOT NULL
            )
        """)
        now_ts = datetime.utcnow().isoformat()
        for t, snap in snapshots.items():
            # Preserve exact DDL and rows idempotently
            arch_cur.execute(f'DROP TABLE IF EXISTS "{t}"')
            arch_cur.execute(snap["ddl"])
            if snap["rows"]:
                col_names = ", ".join(f'"{c}"' for c in snap["columns"])
                placeholders = ", ".join("?" for _ in snap["columns"])
                arch_cur.executemany(
                    f'INSERT INTO "{t}" ({col_names}) VALUES ({placeholders})',
                    snap["rows"],
                )
            arch_cur.execute(
                """
                INSERT OR REPLACE INTO _tier0_archive_manifest
                    (table_name, source_label, row_count, rows_sha256, archived_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (t, source_label, snap["row_count"], snap["sha256"], now_ts),
            )
        arch_conn.commit()

        # Verify archive DB integrity and exact parity before touching runtime DB
        arch_cur.execute("PRAGMA integrity_check;")
        arch_integrity = arch_cur.fetchall()
        if arch_integrity != [("ok",)]:
            raise RuntimeError(f"Archive DB failed integrity_check: {arch_integrity}")

        verified_parity = {}
        for t, snap in snapshots.items():
            arch_snap = _fetch_table_snapshot(arch_conn, t)
            if arch_snap["row_count"] != snap["row_count"] or arch_snap["sha256"] != snap["sha256"]:
                raise RuntimeError(
                    f"Archive parity mismatch for {t}: "
                    f"rows {arch_snap['row_count']}!={snap['row_count']} or hash mismatch"
                )
            verified_parity[t] = {
                "row_count": arch_snap["row_count"],
                "sha256": arch_snap["sha256"],
                "parity_verified": True,
            }
    finally:
        arch_conn.close()

    dropped = False
    if drop_from_runtime:
        drop_stmts = [f'DROP TABLE IF EXISTS "{t}"' for t in targets]
        execute_batch(runtime_conn, drop_stmts)
        dropped = True

    return {
        "status": "ARCHIVED_AND_VERIFIED",
        "source_label": source_label,
        "archive_db_path": archive_db_path,
        "tables": verified_parity,
        "dropped": dropped,
    }


def extract_tier0_sqlite_file(
    runtime_db_path: str,
    archive_db_path: str,
    drop_from_runtime: bool = False,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Convenience wrapper executing Tier 0 archive + post-drop SQLite integrity check."""
    conn = sqlite3.connect(runtime_db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        res = extract_tier0_from_connection(
            conn, archive_db_path, drop_from_runtime=drop_from_runtime, dry_run=dry_run, source_label="local_sqlite"
        )
        if drop_from_runtime and not dry_run:
            cur = conn.cursor()
            cur.execute("PRAGMA integrity_check;")
            res["post_drop_integrity_check"] = cur.fetchall()
            cur.execute("PRAGMA foreign_key_check;")
            res["post_drop_foreign_key_check"] = cur.fetchall()
        return res
    finally:
        conn.close()


def rollback_tier0_from_archive(
    runtime_conn: Any,
    archive_db_path: str,
) -> Dict[str, Any]:
    """Restores Tier 0 tables cleanly from archive_db_path back into runtime_conn."""
    if not os.path.exists(archive_db_path):
        raise FileNotFoundError(f"Archive database missing: {archive_db_path}")

    arch_conn = sqlite3.connect(f"file:{os.path.abspath(archive_db_path)}?mode=ro", uri=True)
    try:
        arch_tables = set(list_user_tables(arch_conn))
        to_restore = [t for t in TIER0_TABLES if t in arch_tables]
        restored = {}
        for t in to_restore:
            snap = _fetch_table_snapshot(arch_conn, t)
            stmts: List[Any] = [f'DROP TABLE IF EXISTS "{t}"', snap["ddl"]]
            col_names = ", ".join(f'"{c}"' for c in snap["columns"])
            for r in snap["rows"]:
                vals = ", ".join(sql_literal(v) for v in r)
                stmts.append(f'INSERT INTO "{t}" ({col_names}) VALUES ({vals})')
            # Execute in manageable chunks cleanly
            for i in range(0, len(stmts), 100):
                execute_batch(runtime_conn, stmts[i:i + 100])
            restored[t] = {"row_count": snap["row_count"], "sha256": snap["sha256"]}
        return {"status": "ROLLED_BACK", "restored": restored}
    finally:
        arch_conn.close()
