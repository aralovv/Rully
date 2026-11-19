import os

# Explicitly ensure test suite always runs against local isolated SQLite
os.environ["TURSO_DATABASE_URL"] = ""
os.environ["TURSO_AUTH_TOKEN"] = ""
os.environ["ENVIRONMENT"] = "testing"
