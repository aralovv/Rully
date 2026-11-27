"""
Unified Database Adapter for RULLY Avtotest.
Supports both local SQLite (offline development) and Turso cloud libSQL (high-concurrency production).
Provides drop-in compatibility with standard Python sqlite3 Connection, Cursor, and Row interfaces.
"""

import os
import sqlite3
import threading
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

    def _raise_sqlite_for_turso_error(msg: str, code: str = "UNKNOWN"):
        low = f"{code} {msg}".lower()
        if "constraint" in low or "unique" in low or "foreign key" in low:
            raise sqlite3.IntegrityError(msg)
        raise sqlite3.OperationalError(f"{code}: {msg}")

    async def _patched_execute(self, stmt, args=None):
        request = {"stmt": _stmt_to_proto(stmt, args)}
        try:
            response = await self._send("POST", "v1/execute", request)
            if isinstance(response, dict) and "message" in response and "result" not in response:
                _raise_sqlite_for_turso_error(response["message"], response.get("code", "UNKNOWN"))
            return _result_set_from_proto(response["result"])
        except Exception as exc:
            if hasattr(libsql_client, "LibsqlError") and isinstance(exc, libsql_client.LibsqlError):
                if _is_transient_turso_error(exc):
                    raise
                _raise_sqlite_for_turso_error(str(exc), getattr(exc, "code", "UNKNOWN"))
            raise

    async def _patched_batch(self, stmts):
        request = {"batch": _batch_to_proto(stmts)}
        try:
            response = await self._send("POST", "v1/batch", request)
            if isinstance(response, dict) and "message" in response and "result" not in response:
                _raise_sqlite_for_turso_error(response["message"], response.get("code", "UNKNOWN"))
            proto_res = response["result"]
            return _batch_results_from_proto(proto_res, len(stmts))
        except Exception as exc:
            if hasattr(libsql_client, "LibsqlError") and isinstance(exc, libsql_client.LibsqlError):
                if _is_transient_turso_error(exc):
                    raise
                _raise_sqlite_for_turso_error(str(exc), getattr(exc, "code", "UNKNOWN"))
            raise

    HttpClient.execute = _patched_execute
    HttpClient.batch = _patched_batch

    HAS_LIBSQL = True
except ImportError:
    HAS_LIBSQL = False


_thread_local = threading.local()

def get_shared_turso_client(url: str, token: str):
    """
    Thread-safe per-thread persistent libSQL client using threading.local().
    Eliminates socket race conditions when executing sync database operations in FastAPI worker threadpool.
    """
    client = getattr(_thread_local, "turso_client", None)
    if client is None or getattr(client, "closed", False):
        client = libsql_client.create_client_sync(url=url, auth_token=token)
        _thread_local.turso_client = client
    return client


def close_shared_turso_client() -> None:
    """Explicitly closes the current thread's shared Turso client (useful for CLI exit)."""
    client = getattr(_thread_local, "turso_client", None)
    if client is not None and not getattr(client, "closed", False):
        try:
            client.close()
        except Exception:
            pass
    _thread_local.turso_client = None


def _is_transient_turso_error(exc: Exception) -> bool:
    err_msg = f"{type(exc).__name__} {exc}".lower()
    terms = ("disconnect", "connection", "closed", "socket", "timeout", "reset", "broken", "eof")
    return any(term in err_msg for term in terms)


def _refresh_shared_turso_client(url: str, token: str):
    close_shared_turso_client()
    client = libsql_client.create_client_sync(
        url=url.replace("libsql://", "https://"),
        auth_token=token,
    )
    _thread_local.turso_client = client
    return client


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

    def __getitem__(self, key: Union[int, slice, str]):
        if isinstance(key, (int, slice)):
            return self._raw[key]
        return self._dict[key]

    def __contains__(self, key: str) -> bool:
        return key in self._dict

    def __len__(self) -> int:
        return len(self._columns)

    def __iter__(self):
        # Match sqlite3.Row: iterate column values in positional order while
        # dict(row) works via .keys() + __getitem__.
        return (self._raw[i] for i in range(len(self._columns)))

    def __eq__(self, other: object) -> bool:
        if isinstance(other, TursoRow):
            return tuple(self) == tuple(other)
        if isinstance(other, tuple):
            return tuple(self) == other
        return NotImplemented

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
    def __init__(self, client, url: Optional[str] = None, token: Optional[str] = None, conn: Optional["TursoConnection"] = None):
        self._client = client
        self._conn = conn
        self._url = url or os.getenv("TURSO_DATABASE_URL", "").strip()
        self._token = token or os.getenv("TURSO_AUTH_TOKEN", "").strip()
        self._current_result = None
        self._row_idx = 0
        self.lastrowid = None
        self.rowcount = -1
        self.description = None

    def _sync_refreshed_client(self, new_client):
        self._client = new_client
        if self._conn is not None and getattr(self._conn, "_shared", False):
            self._conn._client = new_client

    def execute(self, sql: str, params: Optional[Union[List, Tuple, Dict]] = None):
        clean_sql = sql.strip().rstrip(";")
        args = list(params) if params is not None else []

        try:
            res = self._client.execute(clean_sql, args)
        except sqlite3.IntegrityError:
            raise
        except Exception as e:
            if HAS_LIBSQL and hasattr(libsql_client, "LibsqlError") and isinstance(e, libsql_client.LibsqlError) and not _is_transient_turso_error(e):
                _raise_sqlite_for_turso_error(str(e), getattr(e, "code", "UNKNOWN"))
            if _is_transient_turso_error(e):
                logger.warning(f"Turso client error ({e}), refreshing thread-local persistent connection and retrying...")
                new_client = _refresh_shared_turso_client(self._url, self._token)
                self._sync_refreshed_client(new_client)
                try:
                    res = self._client.execute(clean_sql, args)
                except Exception as retry_e:
                    if HAS_LIBSQL and hasattr(libsql_client, "LibsqlError") and isinstance(retry_e, libsql_client.LibsqlError):
                        _raise_sqlite_for_turso_error(str(retry_e), getattr(retry_e, "code", "UNKNOWN"))
                    raise
            elif isinstance(e, sqlite3.OperationalError):
                raise
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
        if self._conn is not None:
            results = self._conn.batch(stmts)
        else:
            results = self._client.batch(stmts)
        self.rowcount = sum(getattr(r, "rows_affected", 0) for r in results)
        return self

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
        return TursoCursor(self._client, url=self.url, token=self.token, conn=self)

    def execute(self, sql: str, params: Optional[Union[List, Tuple]] = None) -> TursoCursor:
        cur = self.cursor()
        return cur.execute(sql, params)

    def executescript(self, script: str):
        stmts = [s.strip() for s in script.split(";") if s.strip()]
        return self.batch(stmts)

    def batch(self, stmts: List[Union[str, Tuple[str, Any]]]):
        """Execute a batch of statements in a single round-trip HTTP request."""
        if not stmts:
            return []
        formatted_stmts = []
        for s in stmts:
            if isinstance(s, (tuple, list)):
                sql = s[0].strip().rstrip(";")
                params = list(s[1]) if len(s) > 1 and s[1] is not None else []
                formatted_stmts.append((sql, params))
            else:
                formatted_stmts.append(s.strip().rstrip(";"))
        try:
            return self._client.batch(formatted_stmts)
        except sqlite3.IntegrityError:
            raise
        except Exception as e:
            if _is_transient_turso_error(e) and self._shared:
                logger.warning(f"Turso batch client error ({e}), refreshing shared client and retrying once...")
                self._client = _refresh_shared_turso_client(self.url, self.token)
                try:
                    return self._client.batch(formatted_stmts)
                except Exception as retry_e:
                    if HAS_LIBSQL and hasattr(libsql_client, "LibsqlError") and isinstance(retry_e, libsql_client.LibsqlError):
                        _raise_sqlite_for_turso_error(str(retry_e), getattr(retry_e, "code", "UNKNOWN"))
                    raise
            if HAS_LIBSQL and hasattr(libsql_client, "LibsqlError") and isinstance(e, libsql_client.LibsqlError):
                _raise_sqlite_for_turso_error(str(e), getattr(e, "code", "UNKNOWN"))
            raise

    def commit(self):
        pass

    def rollback(self):
        logger.debug(
            "TursoConnection.rollback() is a no-op on autocommitted single HTTP statements; "
            "use execute_batch() for atomic multi-statement writes."
        )

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


def _get_turso_credentials() -> Tuple[str, str]:
    url = os.getenv("TURSO_DATABASE_URL", "").strip()
    token = os.getenv("TURSO_AUTH_TOKEN", "").strip()
    return url, token


def is_turso_enabled() -> bool:
    """Returns True if Turso cloud database credentials are dynamically configured."""
    url, token = _get_turso_credentials()
    return bool(url and token and HAS_LIBSQL)


def get_db_connection(db_path: Optional[str] = None):
    """
    Unified database connection factory.
    Returns TursoConnection if TURSO_DATABASE_URL is set; otherwise local sqlite3.Connection.
    """
    if is_turso_enabled():
        url, token = _get_turso_credentials()
        http_url = url.replace("libsql://", "https://")
        return TursoConnection(url=http_url, token=token)

    resolved_path = db_path or os.getenv("DB_PATH", "master_database.sqlite")
    conn = sqlite3.connect(resolved_path, timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        conn.execute("PRAGMA journal_mode = WAL;")
    except Exception:
        pass
    return conn


def execute_batch(conn: Union[sqlite3.Connection, TursoConnection], stmts: List[Union[str, Tuple[str, Any]]]) -> List[Any]:
    """
    Executes a sequence of SQL statements atomically.
    Uses Turso libSQL client's native batch() for a single HTTP round-trip when available,
    or sequential cursor execution with transaction commit/rollback for standard SQLite.
    """
    if not stmts:
        return []
    if hasattr(conn, "batch"):
        return conn.batch(stmts)

    cur = conn.cursor()
    results = []
    try:
        for s in stmts:
            if isinstance(s, (tuple, list)):
                sql = s[0]
                params = s[1] if len(s) > 1 and s[1] is not None else ()
                cur.execute(sql, params)
            else:
                cur.execute(s)
        conn.commit()
        return results
    except Exception:
        conn.rollback()
        raise


def _row_to_dict(row: Any, columns: Tuple[str, ...] = ()) -> Dict[str, Any]:
    if isinstance(row, dict):
        return dict(row)
    if hasattr(row, "asdict"):
        return row.asdict()
    if hasattr(row, "keys"):
        return {k: row[k] for k in row.keys()}
    return dict(zip(columns, row))


def fetch_batch_dicts(
    conn: Union[sqlite3.Connection, TursoConnection],
    stmts: List[Union[str, Tuple[str, Any]]],
) -> List[List[Dict[str, Any]]]:
    """
    Executes N read-only SQL queries in 1 atomic HTTP round-trip on Turso (or sequential cursor
    execution on local SQLite) and returns normalized List[List[Dict[str, Any]]] per query.
    """
    if not stmts:
        return []
    if hasattr(conn, "batch"):
        raw_results = conn.batch(stmts)
        out: List[List[Dict[str, Any]]] = []
        for rs in raw_results:
            cols = tuple(getattr(rs, "columns", ()) or ())
            rows = getattr(rs, "rows", None) or []
            out.append([_row_to_dict(r, cols) for r in rows])
        return out

    cur = conn.cursor()
    out = []
    for s in stmts:
        if isinstance(s, (tuple, list)):
            sql = s[0]
            params = s[1] if len(s) > 1 and s[1] is not None else ()
            cur.execute(sql, params)
        else:
            cur.execute(s)
        cols = tuple(d[0] for d in (cur.description or ()))
        rows = cur.fetchall()
        out.append([_row_to_dict(r, cols) for r in rows])
    return out

