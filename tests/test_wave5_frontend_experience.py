"""
Wave 5 Student Frontend, Public Freemium Web, Topic Pagination, PWA & Zero-PII/Zero-XSS Suite.
"""

import json
import os
from pathlib import Path
import subprocess

from fastapi.testclient import TestClient

from src.api.deps import invalidate_user_cache
from src.api.main import app, create_app
from src.api.routes_theory import engine
from src.api.security import generate_dev_init_data
from src.bot.database import BotDatabase


ROOT_DIR = Path(__file__).resolve().parent.parent


def test_public_freemium_overview_and_diagnostic_in_production_mode(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    prod_app = create_app(public_only=True)
    client = TestClient(prod_app)

    ov = client.get("/api/public/overview?lang=uz_latn")
    assert ov.status_code == 200
    data = ov.json()
    assert data["ok"] is True
    assert data["total_questions"] >= 1300
    assert len(data["categories"]) >= 40
    qs = data["diagnostic_questions"]
    assert len(qs) == 5
    # Verify NO correct_option_key or explanation leaks before grading!
    assert all(q.get("correct_option_key") is None for q in qs)
    assert all(q.get("explanation") is None for q in qs)

    # Check grading endpoint
    answers = [{"canonical_id": q["canonical_id"], "selected_key": q["options"][0]["option_key"]} for q in qs]
    chk = client.post("/api/public/diagnostic/check", json={"language": "uz_latn", "answers": answers})
    assert chk.status_code == 200
    res = chk.json()
    assert res["ok"] is True
    assert res["total"] == 5
    assert len(res["items"]) == 5
    assert all(it.get("correct_option_key") in ("A", "B", "C", "D", "E") for it in res["items"])


def test_category_unseen_first_and_full_coverage_above_30():
    client = TestClient(app)
    db = BotDatabase(os.getenv("DB_PATH"))
    uid = 99554411
    token = generate_dev_init_data(user_id=uid)
    invalidate_user_cache(uid)

    # Pick a large category with > 30 questions
    cats = engine.get_categories("uz_latn")
    big_cat = next(c for c in cats if c["question_count"] > 35)
    cat_id = big_cat["category_id"]
    total_cnt = big_cat["question_count"]

    # Fetch first 30
    all_q = engine.get_questions_by_category(cat_id, language="uz_latn", limit=total_cnt)
    assert len(all_q) == total_cnt
    first_30_ids = {q.canonical_id for q in all_q[:30]}

    # Mark first 30 as solved
    solved_mock = set(first_30_ids)
    next_batch = engine.get_questions_by_category(cat_id, language="uz_latn", limit=30, solved_ids=solved_mock)
    # Every question #31..N must be prioritized ahead of already solved questions!
    unseen_expected_cnt = total_cnt - 30
    unseen_returned = [q for q in next_batch[:unseen_expected_cnt] if q.canonical_id not in first_30_ids]
    assert len(unseen_returned) == min(30, unseen_expected_cnt)

    # API session start reaches all questions when requested or paginated via offset
    res_off = client.post(
        "/api/session/start",
        json={"session_type": "CATEGORY", "category_id": cat_id, "total_questions": 20, "offset": 30, "language": "uz_latn"},
        headers={"X-Telegram-Init-Data": token},
    )
    assert res_off.status_code == 200
    assert len(res_off.json()["questions"]) >= 1

    # Mistakes bank is unlocked for Free user (once a mistake exists)
    with db._get_connection() as conn:
        conn.execute("DELETE FROM user_mistakes WHERE user_id = ?", (uid,))
        conn.commit()
    db.record_mistake(uid, all_q[0].canonical_id)
    invalidate_user_cache(uid)
    m_res = client.post(
        "/api/session/start",
        json={"session_type": "MISTAKES", "total_questions": 10, "language": "uz_latn"},
        headers={"X-Telegram-Init-Data": token},
    )
    assert m_res.status_code == 200


def test_wave5_frontend_assets_pwa_i18n_and_zero_pii():
    client = TestClient(app)

    html = (ROOT_DIR / "static" / "index.html").read_text(encoding="utf-8")
    for pii in ("ANVARJON ARALOV", "9860 0000 0000 5370"):
        assert pii not in html
    assert 'id="quiz-ai-drawer"' in html
    assert 'id="onboarding-modal"' in html
    assert 'rel="manifest"' in html

    profile_js = (ROOT_DIR / "static" / "js" / "views" / "profile.js").read_text(encoding="utf-8")
    for pii in ("ANVARJON ARALOV", "9860 0000 0000 5370"):
        assert pii not in profile_js
    assert "safeRichHtml" in profile_js

    ref_js = (ROOT_DIR / "static" / "js" / "views" / "reference.js").read_text(encoding="utf-8")
    for tok in ("plate_range", "plate_down", "circle_slash", "prov_ref_law"):
        assert tok in ref_js

    quiz_js = (ROOT_DIR / "static" / "js" / "views" / "quiz.js").read_text(encoding="utf-8")
    assert "recalibrate: true" in quiz_js
    assert 'data-srs-rate="1"' in quiz_js
    assert "rully_quiz_draft" in quiz_js

    amaliy_js = (ROOT_DIR / "static" / "js" / "views" / "amaliy.js").read_text(encoding="utf-8")
    assert "avtodrom-stage" not in amaliy_js
    assert "SIM_MANEUVERS" not in amaliy_js
    assert "renderChecklistTab" not in amaliy_js
    assert "renderScenariosTab" not in amaliy_js
    assert "renderModulesTab" in amaliy_js
    assert "PENALTY_ITEMS" in amaliy_js

    css = (ROOT_DIR / "static" / "css" / "rully.css").read_text(encoding="utf-8")
    assert "--text-muted: #94A3B8;" in css

    # Static delivery checks for PWA + lazy i18n bundles
    assert client.get("/static/manifest.json").status_code == 200
    assert client.get("/static/sw.js").status_code == 200
    for lang in ("uz_latn", "uz_cyrl", "ru"):
        r = client.get(f"/static/i18n/{lang}.json")
        assert r.status_code == 200
        bundle = json.loads(r.text)
        assert "srs_rate_again" in bundle and "guest_diag_btn" in bundle

    # Verify all JS files pass node --check cleanly
    for js_file in ROOT_DIR.joinpath("static").rglob("*.js"):
        chk = subprocess.run(["node", "--check", str(js_file)], capture_output=True, text=True)
        assert chk.returncode == 0, f"{js_file}: {chk.stderr}"
