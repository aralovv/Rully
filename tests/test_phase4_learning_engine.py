"""
Phase 4 Verification Suite — Road Signs Explorer, VMQ 172/408 Law Reader,
Legal Provenance Exposure, Shpargalka Full Rules & Quiz UX Upgrades.
"""
import re
from pathlib import Path
from fastapi.testclient import TestClient

from src.api.main import app
from src.avtotest_product import AvtotestProductEngine
from src.db.reference_catalog import get_road_signs_reference, get_law_reference


ROOT_DIR = Path(__file__).resolve().parent.parent
client = TestClient(app)


def test_reference_signs_api_multilingual_and_category_mapping():
    engine = AvtotestProductEngine("master_database.sqlite")
    valid_cat_ids = {c["category_id"] for c in engine.get_categories("uz_latn")}

    for lang in ("uz_latn", "uz_cyrl", "ru"):
        res = client.get(f"/api/reference/signs?lang={lang}")
        assert res.status_code == 200
        payload = res.json()
        assert payload["ok"] is True
        assert payload["language"] == lang
        assert len(payload["groups"]) >= 6
        assert len(payload["signs"]) >= 30

        for grp in payload["groups"]:
            assert grp["category_id"] in valid_cat_ids
            assert grp["name"].strip()
            assert grp["distance_rule"].strip()

        for sign in payload["signs"]:
            assert sign["code"]
            assert sign["name"].strip()
            assert sign["rule"].strip()
            assert sign["category_id"] in valid_cat_ids


def test_reference_law_api_all_29_chapters_and_norms():
    for lang in ("uz_latn", "uz_cyrl", "ru"):
        res = client.get(f"/api/reference/law?lang={lang}")
        assert res.status_code == 200
        payload = res.json()
        assert payload["ok"] is True
        assert payload["total_chapters"] == 29
        assert len(payload["chapters"]) == 29
        assert [c["chapter"] for c in payload["chapters"]] == list(range(1, 30))
        assert len(payload["norms"]) >= 4
        for ch in payload["chapters"]:
            assert ch["title"].strip()
            assert ch["summary"].strip()


def test_provenance_metadata_exposed_in_engine_and_api():
    engine = AvtotestProductEngine("master_database.sqlite")
    sample = engine.get_random_practice(count=1, language="uz_latn")[0]
    fb = engine.check_answer(sample.canonical_id, sample.correct_option_key, language="uz_latn")
    assert hasattr(sample, "legal_verification_status")
    assert hasattr(fb, "legal_verification_status")
    assert sample.legal_verification_status in (
        "VERIFIED_PRIMARY_LAW",
        "VERIFIED_FIRST_AID_OR_TECH",
        "UNRESOLVED_LEGAL_REVIEW",
    )


def test_phase4_frontend_modules_and_i18n_parity():
    ref_js = (ROOT_DIR / "static" / "js" / "views" / "reference.js").read_text(encoding="utf-8")
    assert "renderSignSvg" in ref_js
    assert "renderSignsExplorer" in ref_js
    assert "renderLawExplorer" in ref_js
    assert "renderProvenanceBadge" in ref_js
    assert "openLawModal" in ref_js

    prep_js = (ROOT_DIR / "static" / "js" / "views" / "prepare.js").read_text(encoding="utf-8")
    assert "data-prep-tab=\"reference\"" in prep_js
    assert "data-ref-mode=\"signs\"" in prep_js
    assert "data-ref-mode=\"rules\"" in prep_js
    assert "R.renderSignsExplorer" in prep_js
    assert "R.renderLawExplorer" in prep_js

    quiz_js = (ROOT_DIR / "static" / "js" / "views" / "quiz.js").read_text(encoding="utf-8")
    assert "R.renderProvenanceBadge" in quiz_js
    assert "quiz-autonext-btn" in quiz_js
    assert "data-rev-filter" in quiz_js

    prof_js = (ROOT_DIR / "static" / "js" / "views" / "profile.js").read_text(encoding="utf-8")
    assert "cs.rules_boxes" in prof_js
    assert "cs-search-input" in prof_js
    assert "R.openInfoModal('rules')" in prof_js

    home_js = (ROOT_DIR / "static" / "js" / "views" / "home.js").read_text(encoding="utf-8")
    assert "guest-tile-signs" in home_js
    assert "guest-tile-rules" in home_js
    assert "tile-tickets" in home_js
    assert "tile-categories" in home_js

    trans_js = (ROOT_DIR / "static" / "js" / "translations.js").read_text(encoding="utf-8")
    for key in (
        "tab_signs:",
        "tab_rules:",
        "ref_signs_title:",
        "ref_law_title:",
        "prov_verified_law:",
        "prov_pending_review:",
        "quiz_auto_next:",
        "review_filter_mistakes:",
        "cs_search_placeholder:",
    ):
        assert len(re.findall(rf"\b{re.escape(key)}", trans_js)) == 3, f"Missing 3-language coverage for {key}"
