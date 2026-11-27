"""
Direct CI Question Sync CLI runner (Phase 4 sync topology offload).
Runs YesPrava & ProPDD incremental diff scraping directly in GitHub Actions against Turso staging
instead of consuming Render's 512MB runtime memory over an HTTP webhook timeout.
"""

import json
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.sync.service import QuestionSyncService


def main() -> int:
    svc = QuestionSyncService(db_path=os.getenv("DB_PATH", "master_database.sqlite"))
    result = svc.check_for_updates(auto_stage=True)
    print(json.dumps({"ok": True, **result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
