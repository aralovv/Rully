import os
import sys
import libsql_client

url = "https://rully-aralovv.aws-ap-south-1.turso.io"
auth_token = "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3OTUwMDczOTYsImlkIjoiMDFhMWVlYzMtNmUwMS03MWJlLTlkMjEtNzAzMjQ0NDY1MDIzIiwia2lkIjoiMlYxQjFiOWpfUDFLWEFjemlRVDdyc0JRODZDQnB0OTUxYWJMRV9Kajd4QSIsInJpZCI6IjRlNjc5N2RlLWJjYWUtNGRkOS04YmNkLWQ3MDIwOWQyNmExOSJ9.Nyrki10bjIRZAd-J6wSZ0mQX84mGl_xzo1B3oJ-Apjy09ScmNKptlteNcPbhAKJMedVELY46I-iLbTpGGGFBBw"

client = libsql_client.create_client_sync(url=url, auth_token=auth_token)
try:
    client.execute("DROP TABLE IF EXISTS test_users;")
    client.execute("CREATE TABLE test_users (id INTEGER PRIMARY KEY, name TEXT);")
    client.batch([
        ("INSERT INTO test_users (id, name) VALUES (?, ?);", [1, "Ali"]),
        ("INSERT INTO test_users (id, name) VALUES (?, ?);", [2, "Vali"]),
    ])
    res = client.execute("SELECT * FROM test_users ORDER BY id;")
    for row in res.rows:
        print("Row:", row.asdict())
    client.execute("DROP TABLE test_users;")
    print("Test passed successfully!")
finally:
    client.close()
