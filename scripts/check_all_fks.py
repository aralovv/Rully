import sqlite3

conn = sqlite3.connect('master_database.sqlite')
cursor = conn.cursor()

# Run PRAGMA foreign_key_check on master_database.sqlite
print("Running PRAGMA foreign_key_check()...")
fk_errors = cursor.execute("PRAGMA foreign_key_check;").fetchall()
print(f"Total FK violations in master_database.sqlite: {len(fk_errors)}")
for err in fk_errors:
    # table, rowid, parent_table, fkid
    table, rowid, parent_table, fkid = err
    row = cursor.execute(f"SELECT * FROM \"{table}\" WHERE rowid = {rowid};").fetchone()
    print(f"  Violation in table '{table}' (rowid {rowid}) referencing '{parent_table}': {row}")

conn.close()
