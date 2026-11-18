"""
Unified Database Adapter for RULLY Avtotest.
Supports both local SQLite (offline development) and Turso cloud libSQL (high-concurrency production).
Provides drop-in compatibility with standard Python sqlite3 Connection, Cursor, and Row interfaces.
"""

import os
import sqlite3
import logging
from typing import Optional, List, Dict, Any, Tuple, Union
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

TURSO_URL = os.getenv("TURSO_DATABASE_URL", "").strip()
TURSO_TOKEN = os.getenv("TURSO_AUTH_TOKEN", "").strip()

try:
    import libsql_client
    import libsql_client.http
    from libsql_client.http import HttpClient
    from libsql_client.hrana.convert import _stmt_to_proto, _result_set_from_proto, _batch_to_proto, _batch_results_from_proto
    
    _orig_execute = HttpClient.execute
    _orig_batch = HttpClient.batch

    async def _patched_execute(self, stmt, args=None):
        request = {"stmt": _stmt_to_proto(stmt, args)}
        response = await self._send("POST", "v1/execute", request)
        if isinstance(response, dict) and "message" in response and "result" not in response:
            msg = response["message"]
            code = response.get("code", "UNKNOWN")
            if "constraint" in msg.lower() or "unique" in msg.lower():
                raise sqlite3.IntegrityError(msg)
            raise sqlite3.OperationalError(f"{code}: {msg}")
        return _result_set_from_proto(response["result"])

    async def _patched_batch(self, stmts):
        request = {"batch": _batch_to_proto(stmts)}
        response = await self._send("POST", "v1/batch", request)
        if isinstance(response, dict) and "message" in response and "result" not in response:
            msg = response["message"]
            code = response.get("code", "UNKNOWN")
            if "constraint" in msg.lower() or "unique" in msg.lower():
                raise sqlite3.IntegrityError(msg)
            raise sqlite3.OperationalError(f"{code}: {msg}")
        proto_res = response["result"]
        return _batch_results_from_proto(proto_res, len(stmts))

    HttpClient.execute = _patched_execute
    HttpClient.batch = _patched_batch

    HAS_LIBSQL = True
except ImportError:
    HAS_LIBSQL = False


_shared_turso_client = None

def get_shared_turso_client(url: str, token: str):
    global _shared_turso_client
    if _shared_turso_client is None or getattr(_shared_turso_client, "closed", False):
        _shared_turso_client = libsql_client.create_client_sync(url=url, auth_token=token)
    return _shared_turso_client


class TursoRow:
    """Drop-in replacement for sqlite3.Row wrapping Turso result rows."""
    __slots__ = ("_raw", "_columns", "_dict")

    def __init__(self, raw_row, columns: Tuple[str, ...]):
        self._raw = raw_row
        self._columns = columns
        if hasattr(raw_row, "asdict"):
            self._dict = raw_row.asdict()
        else:
            self._dict = dict(zip(columns, raw_row))

    def __getitem__(self, key: Union[int, str]):
        if isinstance(key, int):
            return self._raw[key]
        return self._dict[key]

    def __contains__(self, key: str) -> bool:
        return key in self._dict

    def __len__(self) -> int:
        return len(self._columns)

    def __iter__(self):
        # Allows dict(row) to work seamlessly
        return iter(self._dict.items())

    def __repr__(self):
        return f"<TursoRow {self._dict}>"

    def keys(self):
        return self._dict.keys()

    def values(self):
        return self._dict.values()

    def items(self):
        return self._dict.items()

    def get(self, key: str, default: Any = None) -> Any:
        return self._dict.get(key, default)


class TursoCursor:
    """Cursor wrapper for Turso libSQL client."""
    def __init__(self, client):
        self._client = client
        self._current_result = None
        self._row_idx = 0
        self.lastrowid = None
        self.rowcount = -1
        self.description = None

    def execute(self, sql: str, params: Optional[Union[List, Tuple, Dict]] = None):
        clean_sql = sql.strip().rstrip(";")
        args = list(params) if params is not None else []
        
        try:
            res = self._client.execute(clean_sql, args)
        except (sqlite3.IntegrityError, sqlite3.OperationalError):
            raise
        except Exception as e:
            err_msg = str(e).lower()
            if any(term in err_msg for term in ["connection", "closed", "socket", "timeout", "reset", "broken"]):
                logger.warning(f"Turso client error ({e}), refreshing persistent connection and retrying...")
                global _shared_turso_client
                try:
                    if _shared_turso_client and not getattr(_shared_turso_client, "closed", False):
                        _shared_turso_client.close()
                except Exception:
                    pass
                _shared_turso_client = libsql_client.create_client_sync(url=TURSO_URL, auth_token=TURSO_TOKEN)
                self._client = _shared_turso_client
                res = self._client.execute(clean_sql, args)
            else:
                logger.error(f"Turso execute error on [{clean_sql}]: {e}")
                raise

        self._current_result = res
        self._row_idx = 0
        self.lastrowid = getattr(res, "last_insert_rowid", None)
        self.rowcount = getattr(res, "rows_affected", -1)
        
        if hasattr(res, "columns") and res.columns:
            self.description = tuple((col, None, None, None, None, None, None) for col in res.columns)
        else:
            self.description = None
        return self

    def executemany(self, sql: str, seq_of_params: List[Union[List, Tuple]]):
        clean_sql = sql.strip().rstrip(";")
        stmts = [(clean_sql, list(p)) for p in seq_of_params]
        if not stmts:
            return self
        try:
            results = self._client.batch(stmts)
            self.rowcount = sum(getattr(r, "rows_affected", 0) for r in results)
            return self
        except Exception as e:
            logger.error(f"Turso executemany error: {e}")
            raise

    def fetchone(self) -> Optional[TursoRow]:
        if not self._current_result or self._row_idx >= len(self._current_result.rows):
            return None
        raw_row = self._current_result.rows[self._row_idx]
        self._row_idx += 1
        return TursoRow(raw_row, self._current_result.columns)

    def fetchall(self) -> List[TursoRow]:
        if not self._current_result:
            return []
        cols = self._current_result.columns
        rows = [TursoRow(r, cols) for r in self._current_result.rows[self._row_idx:]]
        self._row_idx = len(self._current_result.rows)
        return rows

    def close(self):
        self._current_result = None


class TursoConnection:
    """Connection wrapper for Turso libSQL client providing sqlite3-like interface with persistent connection pooling."""
    def __init__(self, url: str, token: str, shared: bool = True):
        if not HAS_LIBSQL:
            raise RuntimeError("libsql-client package is required to connect to Turso.")
        self.url = url
        self.token = token
        self._shared = shared
        if shared:
            self._client = get_shared_turso_client(url, token)
        else:
            self._client = libsql_client.create_client_sync(url=url, auth_token=token)
        self.row_factory = None

    def cursor(self) -> TursoCursor:
        return TursoCursor(self._client)

    def execute(self, sql: str, params: Optional[Union[List, Tuple]] = None) -> TursoCursor:
        cur = self.cursor()
        return cur.execute(sql, params)

    def executescript(self, script: str):
        stmts = [s.strip() for s in script.split(";") if s.strip()]
        return self._client.batch(stmts)

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        # Keep persistent pooled connection open across queries; only close if dedicated
        if not self._shared and hasattr(self, "_client") and self._client and not self._client.closed:
            self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.rollback()
        else:
            self.commit()
        return False


def is_turso_enabled() -> bool:
    """Returns True if Turso cloud database credentials are fully configured."""
    return bool(TURSO_URL and TURSO_TOKEN and HAS_LIBSQL)


def get_db_connection(db_path: str = "master_database.sqlite"):
    """
    Unified database connection factory.
    Returns TursoConnection if TURSO_DATABASE_URL is set; otherwise local sqlite3.Connection.
    """
    if is_turso_enabled():
        return TursoConnection(url=TURSO_URL, token=TURSO_TOKEN)
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn
