import libsql_client
import os
from dotenv import load_dotenv

load_dotenv()
url = os.getenv("TURSO_DATABASE_URL", "https://rully-aralovv.aws-ap-south-1.turso.io")
auth_token = os.getenv("TURSO_AUTH_TOKEN", "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3OTUwMDczOTYsImlkIjoiMDFhMWVlYzMtNmUwMS03MWJlLTlkMjEtNzAzMjQ0NDY1MDIzIiwia2lkIjoiMlYxQjFiOWpfUDFLWEFjemlRVDdyc0JRODZDQnB0OTUxYWJMRV9Kajd4QSIsInJpZCI6IjRlNjc5N2RlLWJjYWUtNGRkOS04YmNkLWQ3MDIwOWQyNmExOSJ9.Nyrki10bjIRZAd-J6wSZ0mQX84mGl_xzo1B3oJ-Apjy09ScmNKptlteNcPbhAKJMedVELY46I-iLbTpGGGFBBw")

client = libsql_client.create_client_sync(url=url, auth_token=auth_token)
try:
    tables = client.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';").rows
    print(f"Total tables on Turso: {len(tables)}")
    for t in tables:
        name = t[0]
        cnt = client.execute(f'SELECT COUNT(*) FROM "{name}";').rows[0][0]
        if cnt > 0:
            print(f"  {name}: {cnt} rows")
finally:
    client.close()
