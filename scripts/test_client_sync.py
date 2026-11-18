import libsql_client
import os
from dotenv import load_dotenv

load_dotenv()

url = "https://rully-aralovv.aws-ap-south-1.turso.io"
auth_token = "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3OTUwMDczOTYsImlkIjoiMDFhMWVlYzMtNmUwMS03MWJlLTlkMjEtNzAzMjQ0NDY1MDIzIiwia2lkIjoiMlYxQjFiOWpfUDFLWEFjemlRVDdyc0JRODZDQnB0OTUxYWJMRV9Kajd4QSIsInJpZCI6IjRlNjc5N2RlLWJjYWUtNGRkOS04YmNkLWQ3MDIwOWQyNmExOSJ9.Nyrki10bjIRZAd-J6wSZ0mQX84mGl_xzo1B3oJ-Apjy09ScmNKptlteNcPbhAKJMedVELY46I-iLbTpGGGFBBw"

client = libsql_client.create_client_sync(url=url, auth_token=auth_token)
print("ClientSync methods:", [m for m in dir(client) if not m.startswith("_")])

res = client.execute("SELECT 1 as id, 'hello' as name")
print("Columns:", res.columns)
print("Rows:", res.rows)
first_row = res.rows[0]
print("Row type:", type(first_row))
print("Row items/keys:", [m for m in dir(first_row) if not m.startswith("_")])
print("Access by index:", first_row[0], first_row[1])
try:
    print("Access by key:", first_row["id"], first_row["name"])
except Exception as e:
    print("Access by key failed:", e)

client.close()
