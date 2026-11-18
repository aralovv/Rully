import sys, os
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from src.db_adapter import get_db_connection

conn = get_db_connection()
c = conn.cursor()
c.execute("SELECT user_id, username, first_name, is_pro, subscription_tier FROM telegram_users WHERE user_id = 1956239701 OR username = 'a_aralovv'")
rows = c.fetchall()
print("Found user:", [dict(r) for r in rows])
