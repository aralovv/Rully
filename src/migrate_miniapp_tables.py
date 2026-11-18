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

    # 2. Practical Exam Checklist (Avtodrom va shahar imtihoni nazorat ro'yxati)
    c.execute("""
    CREATE TABLE IF NOT EXISTS practical_checklist (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        item_id TEXT NOT NULL,
        is_completed INTEGER NOT NULL DEFAULT 0,
        updated_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES telegram_users(user_id) ON DELETE CASCADE,
        UNIQUE(user_id, item_id)
    );
    """)

    # 3. Practical Situational Quiz Results (Vaziyatli test natijalari)
    c.execute("""
    CREATE TABLE IF NOT EXISTS practical_quiz_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        scenario_id TEXT NOT NULL,
        selected_option INTEGER NOT NULL,
        is_correct INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES telegram_users(user_id) ON DELETE CASCADE
    );
    """)

    # 4. Learning Streak & Daily Goals
    c.execute("""
    CREATE TABLE IF NOT EXISTS learning_streak (
        user_id INTEGER PRIMARY KEY,
        current_streak INTEGER NOT NULL DEFAULT 1,
        last_active_date TEXT NOT NULL,
        daily_goal_questions INTEGER NOT NULL DEFAULT 20,
        today_questions_count INTEGER NOT NULL DEFAULT 0,
        updated_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES telegram_users(user_id) ON DELETE CASCADE
    );
    """)

    # Indexes for performance
    c.execute("CREATE INDEX IF NOT EXISTS idx_bookmarks_user ON user_bookmarks(user_id);")
    c.execute("CREATE INDEX IF NOT EXISTS idx_checklist_user ON practical_checklist(user_id);")
    c.execute("CREATE INDEX IF NOT EXISTS idx_practical_quiz_user ON practical_quiz_results(user_id);")

    conn.commit()
    conn.close()
    print("Database migration completed successfully!")

if __name__ == "__main__":
    migrate_db()
