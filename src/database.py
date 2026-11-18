import sqlite3
import os
import hashlib
import json
from datetime import datetime
from typing import Optional, List, Dict, Any

DB_PATH = "data/master_database.sqlite"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_code TEXT UNIQUE NOT NULL,
    source_name TEXT NOT NULL,
    source_url TEXT NOT NULL,
    source_type TEXT NOT NULL,
    authority_level TEXT NOT NULL,
    access_method TEXT NOT NULL,
    terms_status TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    parent_id INTEGER,
    FOREIGN KEY(parent_id) REFERENCES categories(id)
);

CREATE TABLE IF NOT EXISTS images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sha256 TEXT UNIQUE NOT NULL,
    filename TEXT NOT NULL,
    original_url TEXT,
    local_path TEXT NOT NULL,
    width INTEGER,
    height INTEGER,
    format TEXT,
    file_size INTEGER,
    license_status TEXT DEFAULT 'PUBLIC_ACCESS',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS questions (
    id TEXT PRIMARY KEY,
    canonical_hash TEXT UNIQUE NOT NULL,
    question_text TEXT NOT NULL,
    category_id INTEGER,
    language TEXT NOT NULL,
    image_id INTEGER,
    explanation TEXT,
    verification_status TEXT NOT NULL DEFAULT 'UNVERIFIED',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(category_id) REFERENCES categories(id),
    FOREIGN KEY(image_id) REFERENCES images(id)
);

CREATE TABLE IF NOT EXISTS answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id TEXT NOT NULL,
    option_key TEXT NOT NULL,
    answer_text TEXT NOT NULL,
    is_correct INTEGER NOT NULL DEFAULT 0,
    sort_order INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY(question_id) REFERENCES questions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS question_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id TEXT NOT NULL,
    source_id INTEGER NOT NULL,
    original_question_id TEXT,
    original_ticket INTEGER,
    original_position INTEGER,
    original_url TEXT,
    original_language TEXT NOT NULL,
    collection_timestamp TEXT NOT NULL,
    raw_payload TEXT,
    FOREIGN KEY(question_id) REFERENCES questions(id) ON DELETE CASCADE,
    FOREIGN KEY(source_id) REFERENCES sources(id)
);

CREATE TABLE IF NOT EXISTS verification_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id TEXT NOT NULL,
    verification_method TEXT NOT NULL,
    verification_result TEXT NOT NULL,
    evidence TEXT,
    verified_at TEXT NOT NULL,
    FOREIGN KEY(question_id) REFERENCES questions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_questions_hash ON questions(canonical_hash);
CREATE INDEX IF NOT EXISTS idx_questions_lang ON questions(language);
CREATE INDEX IF NOT EXISTS idx_answers_qid ON answers(question_id);
CREATE INDEX IF NOT EXISTS idx_qsources_qid ON question_sources(question_id);
CREATE INDEX IF NOT EXISTS idx_images_sha256 ON images(sha256);
"""

def init_db(db_path: str = DB_PATH) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    return conn

def register_initial_sources(conn: sqlite3.Connection):
    sources_data = [
        (
            "yesprava",
            "YesPrava",
            "https://yesprava.uz",
            "ONLINE_PREPARATION_PORTAL",
            "THIRD_PARTY_CURATED",
            "NEXTJS_PRE_RENDERED_DATA_API",
            "PUBLIC_ACCESSIBLE_ROBOTS_PERMITTED",
            datetime.utcnow().isoformat()
        ),
        (
            "propdd",
            "ProPDD",
            "https://propdd.uz",
            "ONLINE_PREPARATION_PORTAL",
            "THIRD_PARTY_CURATED",
            "STATIC_JS_DATA_BUNDLE",
            "PUBLIC_ACCESSIBLE_FRONTEND_DATA",
            datetime.utcnow().isoformat()
        ),
        (
            "yhq_test",
            "YHQ-Test",
            "https://yhq-test.uz",
            "ONLINE_PREPARATION_PORTAL",
            "THIRD_PARTY_CURATED",
            "SERVER_RENDERED_HTML",
            "PUBLIC_ACCESSIBLE_SITEMAP",
            datetime.utcnow().isoformat()
        ),
        (
            "lex_uz",
            "LexUZ National Legislation Database",
            "https://lex.uz",
            "OFFICIAL_STATE_LEGISLATION_PORTAL",
            "STATUTORY_AUTHORITY",
            "LEGAL_DOCUMENTATION_RESOLUTION_172",
            "PUBLIC_LEGAL_RESOURCE",
            datetime.utcnow().isoformat()
        )
    ]
    cur = conn.cursor()
    for s in sources_data:
        cur.execute("""
            INSERT INTO sources (source_code, source_name, source_url, source_type, authority_level, access_method, terms_status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_code) DO UPDATE SET
                source_name=excluded.source_name,
                source_url=excluded.source_url,
                authority_level=excluded.authority_level,
                access_method=excluded.access_method
        """, s)
    conn.commit()

if __name__ == "__main__":
    conn = init_db()
    register_initial_sources(conn)
    cur = conn.cursor()
    cur.execute("SELECT id, source_code, source_name, authority_level FROM sources;")
    rows = cur.fetchall()
    print("Database initialized successfully. Registered sources:")
    for r in rows:
        print(f"  {r[0]}: {r[1]} - {r[2]} ({r[3]})")
    conn.close()
