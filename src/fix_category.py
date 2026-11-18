import sqlite3

conn = sqlite3.connect('data/master_database.sqlite')
cur = conn.cursor()
cur.execute("UPDATE categories SET slug = 'umumiy', name = 'Umumiy qoidalar' WHERE slug = '' OR slug IS NULL OR name = '' OR name IS NULL;")
conn.commit()
print("Cleaned categories, rows updated:", cur.rowcount)
conn.close()
