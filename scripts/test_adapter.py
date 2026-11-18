import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

from src.db_adapter import get_db_connection, is_turso_enabled

print(f"Is Turso enabled: {is_turso_enabled()}")

conn = get_db_connection()
print(f"Connection class: {type(conn)}")

cur = conn.cursor()
cur.execute("SELECT COUNT(*) as q_count FROM canonical_questions;")
row = cur.fetchone()
print(f"Canonical questions count: {row[0]}")

cur.execute("SELECT id, username FROM admin_users LIMIT 1;")
admin_row = cur.fetchone()
print(f"Admin user: id={admin_row['id']}, username={admin_row['username']}")

cur.execute("SELECT id, name FROM subscription_plans;")
plans = cur.fetchall()
print("Plans count:", len(plans))
for p in plans:
    print(f"  Plan: {p['id']} - {p['name']}")

conn.close()
print("Adapter test completed successfully!")
