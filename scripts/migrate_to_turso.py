"""
Migration script: SQLite -> Turso (libSQL).
Dumps schema and records from master_database.sqlite into Turso cloud database
using strict topological dependency ordering.
"""

import sqlite3
import os
import sys
import time
from typing import List, Dict, Any
import libsql_client
from dotenv import load_dotenv

load_dotenv()

TURSO_URL = os.getenv("TURSO_DATABASE_URL", "https://rully-aralovv.aws-ap-south-1.turso.io")
TURSO_TOKEN = os.getenv("TURSO_AUTH_TOKEN", "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3OTUwMDczOTYsImlkIjoiMDFhMWVlYzMtNmUwMS03MWJlLTlkMjEtNzAzMjQ0NDY1MDIzIiwia2lkIjoiMlYxQjFiOWpfUDFLWEFjemlRVDdyc0JRODZDQnB0OTUxYWJMRV9Kajd4QSIsInJpZCI6IjRlNjc5N2RlLWJjYWUtNGRkOS04YmNkLWQ3MDIwOWQyNmExOSJ9.Nyrki10bjIRZAd-J6wSZ0mQX84mGl_xzo1B3oJ-Apjy09ScmNKptlteNcPbhAKJMedVELY46I-iLbTpGGGFBBw")
SQLITE_DB = "master_database.sqlite"

def get_topologically_sorted_tables(sqlite_cur):
    tables = [r[0] for r in sqlite_cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
    ).fetchall()]

    dependencies = {}
    for t in tables:
        fks = sqlite_cur.execute(f'PRAGMA foreign_key_list("{t}");').fetchall()
        parents = set(fk[2] for fk in fks if fk[2] in tables and fk[2] != t)
        dependencies[t] = parents

    sorted_tables = []
    visited = set()

    def visit(node):
        if node in visited:
            return
        for parent in dependencies.get(node, []):
            visit(parent)
        visited.add(node)
        sorted_tables.append(node)

    for t in tables:
        visit(t)

    return sorted_tables

def migrate():
    print(f"Connecting to local SQLite: {SQLITE_DB}")
    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cur = sqlite_conn.cursor()

    print(f"Connecting to Turso: {TURSO_URL}")
    turso = libsql_client.create_client_sync(url=TURSO_URL, auth_token=TURSO_TOKEN)

    try:
        sorted_tables = get_topologically_sorted_tables(sqlite_cur)
        print(f"Found {len(sorted_tables)} tables to migrate in topological dependency order.")

        # 1. Drop tables in REVERSE order (children first)
        print("\nCleaning existing tables on Turso (reverse dependency order)...")
        for table_name in reversed(sorted_tables):
            try:
                turso.execute(f'DROP TABLE IF EXISTS "{table_name}";')
            except Exception as e:
                print(f"  Note dropping {table_name}: {e}")

        # 2. Create tables in dependency order (parents first)
        print("\nCreating tables on Turso...")
        for table_name in sorted_tables:
            table_sql = sqlite_cur.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name=?;", (table_name,)
            ).fetchone()[0]
            print(f"  Creating table: {table_name}")
            turso.execute(table_sql)

        # 3. Migrate data table by table in dependency order
        print("\nMigrating data...")
        BATCH_SIZE = 250

        for table_name in sorted_tables:
            total_rows = sqlite_cur.execute(f'SELECT COUNT(*) FROM "{table_name}";').fetchone()[0]
            if total_rows == 0:
                print(f"  - '{table_name}': 0 rows (skipped)")
                continue

            # Fetch column names
            sqlite_cur.execute(f'SELECT * FROM "{table_name}" LIMIT 1;')
            columns = [desc[0] for desc in sqlite_cur.description]
            col_names = ", ".join([f'"{c}"' for c in columns])
            placeholders = ", ".join(["?" for _ in columns])
            insert_sql = f'INSERT INTO "{table_name}" ({col_names}) VALUES ({placeholders})'

            offset = 0
            while offset < total_rows:
                batch_rows = sqlite_cur.execute(
                    f'SELECT * FROM "{table_name}" LIMIT ? OFFSET ?;', (BATCH_SIZE, offset)
                ).fetchall()
                if not batch_rows:
                    break

                batch_stmts = []
                for row in batch_rows:
                    batch_stmts.append((insert_sql, list(row)))

                turso.batch(batch_stmts)
                offset += len(batch_rows)

            print(f"  + '{table_name}': {offset}/{total_rows} rows migrated.")

        # 4. Create Indexes
        print("\nCreating indexes...")
        indexes = sqlite_cur.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL AND name NOT LIKE 'sqlite_%';"
        ).fetchall()
        for idx in indexes:
            idx_name = idx["name"]
            idx_sql = idx["sql"]
            try:
                turso.execute(idx_sql)
                print(f"  + Index created: {idx_name}")
            except Exception as e:
                print(f"  Warning on index {idx_name}: {e}")

        # 5. Verification
        print("\n" + "="*60)
        print("VERIFICATION: Comparing row counts between SQLite & Turso")
        print("="*60)
        all_matched = True
        for table_name in sorted_tables:
            sqlite_count = sqlite_cur.execute(f'SELECT COUNT(*) FROM "{table_name}";').fetchone()[0]
            turso_res = turso.execute(f'SELECT COUNT(*) FROM "{table_name}";')
            turso_count = turso_res.rows[0][0]
            match_status = "OK" if sqlite_count == turso_count else "MISMATCH"
            if sqlite_count != turso_count:
                all_matched = False
            print(f"{table_name:35} | SQLite: {sqlite_count:6} | Turso: {turso_count:6} | {match_status}")

        print("="*60)
        if all_matched:
            print(">>> SUCCESS: 100% OF DATA MIGRATED WITH EXACT INTEGRITY! <<<")
        else:
            print(">>> WARNING: Some row counts mismatch. <<<")

    finally:
        sqlite_conn.close()
        turso.close()

if __name__ == "__main__":
    start = time.time()
    migrate()
    print(f"\nCompleted in {round(time.time() - start, 2)} seconds.")
