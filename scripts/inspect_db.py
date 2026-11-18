import sqlite3

conn = sqlite3.connect('master_database.sqlite')
cursor = conn.cursor()

tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';").fetchall()
print("Tables and row counts in master_database.sqlite:")
for t in tables:
    name = t[0]
    count = cursor.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
    print(f"  {name}: {count} rows")

indexes = cursor.execute("SELECT name, tbl_name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%';").fetchall()
print("\nIndexes:")
for idx, tbl in indexes:
    print(f"  {idx} on {tbl}")

conn.close()
