import libsql_client

url = "https://rully-aralovv.aws-ap-south-1.turso.io"
auth_token = "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3OTUwMDczOTYsImlkIjoiMDFhMWVlYzMtNmUwMS03MWJlLTlkMjEtNzAzMjQ0NDY1MDIzIiwia2lkIjoiMlYxQjFiOWpfUDFLWEFjemlRVDdyc0JRODZDQnB0OTUxYWJMRV9Kajd4QSIsInJpZCI6IjRlNjc5N2RlLWJjYWUtNGRkOS04YmNkLWQ3MDIwOWQyNmExOSJ9.Nyrki10bjIRZAd-J6wSZ0mQX84mGl_xzo1B3oJ-Apjy09ScmNKptlteNcPbhAKJMedVELY46I-iLbTpGGGFBBw"

client = libsql_client.create_client_sync(url=url, auth_token=auth_token)

try:
    # Test PRAGMA foreign_keys
    res = client.batch([
        "PRAGMA foreign_keys = OFF;",
        "CREATE TABLE IF NOT EXISTS parent (id INTEGER PRIMARY KEY);",
        "CREATE TABLE IF NOT EXISTS child (id INTEGER PRIMARY KEY, p_id INTEGER REFERENCES parent(id));",
        ("INSERT INTO child (id, p_id) VALUES (?, ?);", [1, 999])
    ])
    print("Batch with PRAGMA foreign_keys = OFF succeeded!")
    client.execute("DROP TABLE child;")
    client.execute("DROP TABLE parent;")
finally:
    client.close()
