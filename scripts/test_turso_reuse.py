import time
import os
from dotenv import load_dotenv
load_dotenv()
import libsql_client

url = os.getenv("TURSO_DATABASE_URL")
token = os.getenv("TURSO_AUTH_TOKEN")

print("Test 1: Creating a new client each time (current behavior)")
times1 = []
for i in range(5):
    t0 = time.time()
    client = libsql_client.create_client_sync(url=url, auth_token=token)
    res = client.execute("SELECT COUNT(*) FROM canonical_questions")
    client.close()
    times1.append((time.time() - t0) * 1000)
print(f"Times: {[f'{t:.0f}ms' for t in times1]} | Avg: {sum(times1)/len(times1):.0f}ms")

print("\nTest 2: Reusing a single persistent client (optimized)")
times2 = []
client = libsql_client.create_client_sync(url=url, auth_token=token)
for i in range(5):
    t0 = time.time()
    res = client.execute("SELECT COUNT(*) FROM canonical_questions")
    times2.append((time.time() - t0) * 1000)
client.close()
print(f"Times: {[f'{t:.0f}ms' for t in times2]} | Avg: {sum(times2)/len(times2):.0f}ms")
