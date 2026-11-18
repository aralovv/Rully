import os
import re

files = [
    'src/admin/auth_service.py',
    'src/admin/routes_admin_dashboard.py',
    'src/admin/routes_admin_users.py',
    'src/admin/routes_admin_plans.py',
    'src/admin/routes_admin_cards.py',
    'src/admin/routes_admin_orders.py',
    'src/admin/routes_admin_payments.py',
    'src/admin/routes_admin_logs.py',
    'src/admin/routes_admin_broadcast.py',
    'src/payments/order_manager.py',
    'src/payments/matching_engine.py',
    'src/analytics/tracker.py',
]

target_func = """def _get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn"""

replacement_func = """from src.db_adapter import get_db_connection

def _get_connection():
    return get_db_connection(DB_PATH)"""

for file_path in files:
    if not os.path.exists(file_path):
        continue
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    if target_func in content:
        content = content.replace(target_func, replacement_func)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Patched: {file_path}")
    else:
        print(f"Target not found in: {file_path}")

# Patch staging_manager.py
sm_path = 'src/sync/staging_manager.py'
if os.path.exists(sm_path):
    with open(sm_path, 'r', encoding='utf-8') as f:
        sm_content = f.read()
    sm_target = """    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn"""
    sm_replacement = """    def _get_connection(self):
        from src.db_adapter import get_db_connection
        return get_db_connection(self.db_path)"""
    if sm_target in sm_content:
        sm_content = sm_content.replace(sm_target, sm_replacement)
        with open(sm_path, 'w', encoding='utf-8') as f:
            f.write(sm_content)
        print(f"Patched: {sm_path}")

# Patch mtproto/service.py
mt_path = 'src/mtproto/service.py'
if os.path.exists(mt_path):
    with open(mt_path, 'r', encoding='utf-8') as f:
        mt_content = f.read()
    mt_target = """    def _get_connection(self):
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn"""
    mt_replacement = """    def _get_connection(self):
        from src.db_adapter import get_db_connection
        return get_db_connection(DB_PATH)"""
    if mt_target in mt_content:
        mt_content = mt_content.replace(mt_target, mt_replacement)
        with open(mt_path, 'w', encoding='utf-8') as f:
            f.write(mt_content)
        print(f"Patched: {mt_path}")

print("All modules patched successfully.")
