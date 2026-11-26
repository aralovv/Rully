import os
import atexit
import shutil
import sqlite3
import tempfile

# Quarantine ALL tests to an isolated WAL-safe SQLite copy in temp storage before any src.* import
_ROOT_MASTER = os.path.abspath("master_database.sqlite")
_TEST_TMP_DIR = tempfile.mkdtemp(prefix="rully_pytest_db_")
_ISOLATED_DB = os.path.join(_TEST_TMP_DIR, "master_database.sqlite")

if os.path.exists(_ROOT_MASTER):
    src_conn = sqlite3.connect(_ROOT_MASTER)
    dst_conn = sqlite3.connect(_ISOLATED_DB)
    try:
        src_conn.backup(dst_conn)
    finally:
        dst_conn.close()
        src_conn.close()

atexit.register(lambda: shutil.rmtree(_TEST_TMP_DIR, ignore_errors=True))

# Explicitly ensure test suite always runs against local isolated SQLite
os.environ["DB_PATH"] = _ISOLATED_DB
os.environ["TURSO_DATABASE_URL"] = ""
os.environ["TURSO_AUTH_TOKEN"] = ""
os.environ["ENVIRONMENT"] = "testing"
os.environ["ALLOW_TEST_ACTIVATION"] = "true"
os.environ["SECRET_KEY"] = os.getenv("SECRET_KEY") or "rully_pytest_secret_key_for_isolated_tests_only_2026"
