import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

print("1. Health check:")
r = client.get("/api/health")
print("Status:", r.status_code, r.json())

print("\n2. Theory categories:")
r = client.get("/api/categories")
print("Status:", r.status_code)
if r.status_code == 200:
    data = r.json()
    print("Categories count:", len(data.get("categories", [])))

print("\n3. Quick test questions:")
r = client.get("/api/quick-test")
print("Status:", r.status_code)
if r.status_code == 200:
    data = r.json()
    print("Quick test items:", len(data.get("questions", [])))

print("\n4. Subscription plans:")
r = client.get("/api/plans")
print("Status:", r.status_code, r.json())

print("\n5. User stats preview:")
r = client.get("/api/stats")
print("Status:", r.status_code, r.json())

print("\nFastAPI on Turso test completed successfully!")
