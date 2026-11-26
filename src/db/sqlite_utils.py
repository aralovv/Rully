"""
Shared SQLite / Turso inspection, WAL-safe backup, and checksum utilities.
"""

import base64
import hashlib
import json
import os
import sqlite3
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple


def encode_cell_for_hash(val: Any) -> Any:
    """Normalizes binary BLOB cells so table digests remain deterministic across backends."""
    if isinstance(val, (bytes, bytearray)):
        return {"__blob_b64__": base64.b64encode(bytes(val)).decode("ascii")}
    return val


def compute_rows_sha256(rows: Iterable[Iterable[Any]]) -> str:
    """Computes a deterministic SHA-256 hash over an ordered sequence of table rows."""
    hasher = hashlib.sha256()
    for row in rows:
        encoded = [encode_cell_for_hash(v) for v in row]
        line = json.dumps(encoded, ensure_ascii=False, separators=(",", ":")) + "\n"
        hasher.update(line.encode("utf-8"))
    return hasher.hexdigest()


def compute_file_sha256(file_path: str) -> str:
    """Streams a file from disk and returns its lowercase SHA-256 hex digest."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def backup_sqlite_wal_safe(src_db_path: str, dst_db_path: str, allow_overwrite: bool = False) -> str:
    """
    Creates a transactionally consistent backup using sqlite3.Connection.backup().
    Never uses raw file copies while WAL mode may be active.
    """
    if not os.path.exists(src_db_path):
        raise FileNotFoundError(f"Source SQLite database not found: {src_db_path}")
    if not allow_overwrite and os.path.exists(dst_db_path):
        raise FileExistsError(f"Refusing to overwrite existing backup: {dst_db_path}")

    parent = os.path.dirname(os.path.abspath(dst_db_path))
    if parent:
        os.makedirs(parent, exist_ok=True)

    abs_src = os.path.abspath(src_db_path)
    src_conn = sqlite3.connect(f"file:{abs_src}?mode=ro", uri=True)
    dst_conn = sqlite3.connect(dst_db_path)
    try:
        src_conn.backup(dst_conn)
    finally:
        dst_conn.close()
        src_conn.close()
    return dst_db_path


def _extract_col_name(row: Any) -> str:
    if hasattr(row, "keys") and "name" in row.keys():
        return str(row["name"])
    return str(row[1])


def get_table_columns(conn: Any, table_name: str) -> Set[str]:
    """Returns column names for a table on either SQLite or TursoConnection."""
    cur = conn.cursor()
    cur.execute(f'PRAGMA table_info("{table_name}")')
    return {_extract_col_name(r) for r in cur.fetchall()}


def list_user_tables(conn: Any) -> List[str]:
    """Returns sorted non-internal user table names."""
    cur = conn.cursor()
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    )
    rows = cur.fetchall()
    return [r["name"] if hasattr(r, "keys") and "name" in r.keys() else r[0] for r in rows]


def get_index_names(conn: Any) -> Set[str]:
    """Returns all explicit index names from sqlite_master."""
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type = 'index' AND name NOT LIKE 'sqlite_%'")
    rows = cur.fetchall()
    return {r["name"] if hasattr(r, "keys") and "name" in r.keys() else r[0] for r in rows}


def sql_literal(val: Any) -> str:
    """Formats a Python value safely into a single-quoted SQLite/libSQL literal."""
    if val is None:
        return "NULL"
    if isinstance(val, bool):
        return "1" if val else "0"
    if isinstance(val, (int, float)):
        return repr(val)
    if isinstance(val, (bytes, bytearray)):
        return "X'" + bytes(val).hex() + "'"
    return "'" + str(val).replace("'", "''") + "'"
