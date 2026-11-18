import sqlite3

conn = sqlite3.connect('master_database.sqlite')
cursor = conn.cursor()

print("Schema of session_answers:")
print(cursor.execute("SELECT sql FROM sqlite_master WHERE name='session_answers'").fetchone()[0])

print("\nFK list for session_answers:")
for fk in cursor.execute("PRAGMA foreign_key_list('session_answers')").fetchall():
    print(fk)

# Find which rows in session_answers violate foreign keys
print("\nChecking invalid user_sessions in session_answers:")
bad_sessions = cursor.execute("""
    SELECT DISTINCT sa.session_id FROM session_answers sa
    LEFT JOIN user_sessions us ON sa.session_id = us.session_id
    WHERE us.session_id IS NULL;
""").fetchall()
print("Bad sessions:", bad_sessions)

print("\nChecking invalid canonical_questions in session_answers:")
bad_questions = cursor.execute("""
    SELECT DISTINCT sa.question_id FROM session_answers sa
    LEFT JOIN canonical_questions cq ON sa.question_id = cq.canonical_id
    WHERE cq.canonical_id IS NULL;
""").fetchall()
print("Bad canonical_ids:", bad_questions)

conn.close()
