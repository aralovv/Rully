import sqlite3
from datetime import datetime

def migrate_db(db_path="master_database.sqlite"):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # 1. User Bookmarks
    c.execute("""
    CREATE TABLE IF NOT EXISTS user_bookmarks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        canonical_id TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES telegram_users(user_id) ON DELETE CASCADE,
        FOREIGN KEY(canonical_id) REFERENCES canonical_questions(canonical_id) ON DELETE CASCADE,
        UNIQUE(user_id, canonical_id)
    );
    """)

    # 2. Learning Streak & Daily Goals
    c.execute("""
    CREATE TABLE IF NOT EXISTS learning_streak (
        user_id INTEGER PRIMARY KEY,
        current_streak INTEGER NOT NULL DEFAULT 0,
        last_active_date TEXT NOT NULL,
        daily_goal_questions INTEGER NOT NULL DEFAULT 20,
        today_questions_count INTEGER NOT NULL DEFAULT 0,
        updated_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES telegram_users(user_id) ON DELETE CASCADE
    );
    """)

    # Indexes for performance
    c.execute("CREATE INDEX IF NOT EXISTS idx_bookmarks_user ON user_bookmarks(user_id);")

    conn.commit()
    conn.close()
    print("Database migration completed successfully!")

if __name__ == "__main__":
    migrate_db()
