import sqlite3

conn = sqlite3.connect('master_database.sqlite')
cursor = conn.cursor()

tables = [r[0] for r in cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';").fetchall()]

dependencies = {}
for t in tables:
    fks = cursor.execute(f'PRAGMA foreign_key_list("{t}");').fetchall()
    # fks format: (id, seq, table, from, to, on_update, on_delete, match)
    parents = set(fk[2] for fk in fks if fk[2] in tables and fk[2] != t)
    dependencies[t] = parents

# Topological sort
sorted_tables = []
visited = set()

def visit(node):
    if node in visited:
        return
    for parent in dependencies.get(node, []):
        visit(parent)
    visited.add(node)
    sorted_tables.append(node)

for t in tables:
    visit(t)

print("Topologically sorted tables (Parent -> Child):")
for i, t in enumerate(sorted_tables, 1):
    parents = dependencies.get(t, [])
    print(f"{i:2d}. {t} (Parents: {', '.join(parents) if parents else 'None'})")

conn.close()
