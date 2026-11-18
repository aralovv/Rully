import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.db_adapter import get_db_connection

def create_tables():
    conn = get_db_connection()
    c = conn.cursor()

    print("Creating ai_conversations table...")
    c.execute("""
    CREATE TABLE IF NOT EXISTS ai_conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        session_id TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system', 'model')),
        content TEXT NOT NULL,
        meta_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    c.execute("""
    CREATE INDEX IF NOT EXISTS idx_ai_conv_user ON ai_conversations(user_id, session_id)
    """)

    print("Creating ai_usage_limits table...")
    c.execute("""
    CREATE TABLE IF NOT EXISTS ai_usage_limits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        usage_date DATE NOT NULL,
        request_count INTEGER DEFAULT 1,
        UNIQUE(user_id, usage_date)
    )
    """)

    c.execute("""
    CREATE INDEX IF NOT EXISTS idx_ai_usage ON ai_usage_limits(user_id, usage_date)
    """)

    conn.commit()
    print("Tables created successfully!")

    # Verify
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('ai_conversations', 'ai_usage_limits')")
    print("Existing tables:", [r['name'] for r in c.fetchall()])

if __name__ == '__main__':
    create_tables()
