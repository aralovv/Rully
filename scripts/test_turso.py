import os
import libsql_client
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("TURSO_DATABASE_URL", "https://rully-aralovv.aws-ap-south-1.turso.io")
auth_token = os.getenv("TURSO_AUTH_TOKEN", "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3OTUwMDczOTYsImlkIjoiMDFhMWVlYzMtNmUwMS03MWJlLTlkMjEtNzAzMjQ0NDY1MDIzIiwia2lkIjoiMlYxQjFiOWpfUDFLWEFjemlRVDdyc0JRODZDQnB0OTUxYWJMRV9Kajd4QSIsInJpZCI6IjRlNjc5N2RlLWJjYWUtNGRkOS04YmNkLWQ3MDIwOWQyNmExOSJ9.Nyrki10bjIRZAd-J6wSZ0mQX84mGl_xzo1B3oJ-Apjy09ScmNKptlteNcPbhAKJMedVELY46I-iLbTpGGGFBBw")

print(f"Connecting to Turso: {url}")
client = libsql_client.create_client_sync(url=url, auth_token=auth_token)

res = client.execute("SELECT 1 as test;")
print("Query success! Result:", res.rows)

tables = client.execute("SELECT name FROM sqlite_master WHERE type='table';")
print("Existing tables on Turso:", [r[0] for r in tables.rows])
client.close()
