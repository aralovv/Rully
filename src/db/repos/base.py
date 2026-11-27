"""Base repository shared connection & row normalization helpers."""

from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from src.db_adapter import execute_batch, fetch_batch_dicts, get_db_connection


class BaseRepo:
    """Thin repository base sharing SQLite/Turso connection factory and batch primitives."""

    def __init__(self, conn_factory: Optional[Callable[[], Any]] = None, db_path: Optional[str] = None):
        self.db_path = db_path
        self._conn_factory = conn_factory

    def _get_connection(self):
        if self._conn_factory is not None:
            return self._conn_factory()
        return get_db_connection(self.db_path)

    @staticmethod
    def _batch_read(conn: Any, stmts: List[Union[str, Tuple[str, Any]]]) -> List[List[Dict[str, Any]]]:
        return fetch_batch_dicts(conn, stmts)

    @staticmethod
    def _batch_write(conn: Any, stmts: List[Union[str, Tuple[str, Any]]]) -> List[Any]:
        return execute_batch(conn, stmts)

    @staticmethod
    def _scalar(row: Any, key_or_idx: Union[str, int] = 0, default: Any = 0) -> Any:
        if row is None:
            return default
        if isinstance(row, dict):
            if isinstance(key_or_idx, str):
                val = row.get(key_or_idx, default)
                return default if val is None else val
            vals = list(row.values())
            val = vals[key_or_idx] if key_or_idx < len(vals) else default
            return default if val is None else val
        try:
            val = row[key_or_idx]
            return default if val is None else val
        except Exception:
            return default
