"""
Versioned, SHA-256 Verified Canonical Bundle & Catalog Revision Management.
Implements Blueprint Part VI:
- Atomic generation of data/canonical_bundle.json & canonical_bundle.manifest.json
- Cryptographic SHA-256 integrity envelope over canonical questions payload
- Database-to-bundle drift detection via system_settings.catalog_version
- Safe fallback signaling (CATALOG_BUNDLE_STALE_FALLBACK)
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from src.db_adapter import execute_batch, get_db_connection

logger = logging.getLogger(__name__)

BUNDLE_SCHEMA_VERSION = 2
DEFAULT_BUNDLE_PATH = os.path.join("data", "canonical_bundle.json")
DEFAULT_MANIFEST_PATH = os.path.join("data", "canonical_bundle.manifest.json")
CATALOG_VERSION_KEY = "catalog_version"


def _row_to_dict(row: Any, cols: List[str]) -> Dict[str, Any]:
    if hasattr(row, "keys") and callable(getattr(row, "keys")):
        return {k: row[k] for k in row.keys()}
    return dict(zip(cols, row))


def bump_catalog_version_sql() -> Tuple[str, List[Any]]:
    """
    Returns an atomic upsert statement incrementing system_settings['catalog_version'].
    Safe to append inside any execute_batch() for SQLite and Turso.
    """
    sql = """
    INSERT INTO system_settings (key, value, description, updated_at)
    VALUES (?, '1', 'Canonical question catalog revision', datetime('now'))
    ON CONFLICT(key) DO UPDATE SET
        value = CAST(COALESCE(CAST(value AS INTEGER), 0) + 1 AS TEXT),
        updated_at = datetime('now')
    """
    return (sql.strip(), [CATALOG_VERSION_KEY])


def get_db_catalog_revision(conn: Any) -> Optional[int]:
    """Reads system_settings['catalog_version'] as an integer; returns 0 if unset, None on query error."""
    try:
        cur = conn.cursor()
        cur.execute("SELECT value FROM system_settings WHERE key = ? LIMIT 1", (CATALOG_VERSION_KEY,))
        row = cur.fetchone()
        if not row:
            return 0
        raw_val = row["value"] if hasattr(row, "keys") else row[0]
        return int(raw_val or 0)
    except Exception as exc:
        logger.debug("Unable to read catalog_version from DB: %s", exc)
        return None


def increment_catalog_version(conn: Any) -> int:
    """Increments system_settings['catalog_version'] and returns the new integer revision."""
    execute_batch(conn, [bump_catalog_version_sql()])
    rev = get_db_catalog_revision(conn)
    return int(rev or 1)


def parse_source_providers(raw: Any) -> List[str]:
    """Safely parses JSON array strings or bare legacy provider strings (e.g. 'YESPRAVA')."""
    if not raw:
        return []
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    text = str(raw).strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return [str(x).strip() for x in parsed if str(x).strip()]
        if isinstance(parsed, str) and parsed.strip():
            return [parsed.strip()]
    except Exception:
        pass
    return [part.strip() for part in text.split(",") if part.strip()]


def parse_json_object(raw: Any) -> Dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    try:
        parsed = json.loads(str(raw))
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def compute_canonical_payload_sha256(questions: List[Dict[str, Any]]) -> str:
    """Computes deterministic SHA-256 over the sorted-keys UTF-8 JSON payload of canonical questions."""
    canonical_bytes = json.dumps(
        questions,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical_bytes).hexdigest()


def build_canonical_bundle(conn: Any, include_editorial_metadata: bool = True) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Reads canonical questions, translations, answers, categories, and catalog_version
    to construct a Schema v2 verified bundle plus detached manifest.
    """
    cur = conn.cursor()

    cur.execute("PRAGMA table_info(canonical_questions)")
    cq_col_names = {r[1] if not hasattr(r, "keys") else r["name"] for r in cur.fetchall()}

    extra_legal_cols = ""
    if {"legal_verification_status", "legal_doc_title", "legal_doc_url", "legal_chapter", "legal_clause", "legal_effective_date"}.issubset(cq_col_names):
        extra_legal_cols = (
            ", cq.legal_verification_status, cq.legal_doc_title, cq.legal_doc_url, "
            "cq.legal_chapter, cq.legal_clause, cq.legal_effective_date"
        )

    cur.execute(
        f"""
        SELECT cq.canonical_id, cq.category_id, cq.category_name, cq.primary_image_id, cq.has_image,
               cq.correct_option_key, cq.legal_reference, cq.legal_act_title, cq.verification_status,
               cq.deduplication_status, cq.source_providers, cq.source_metadata, cq.rights_review_status,
               cq.created_at, cq.updated_at,
               im.local_path AS image_path, im.sha256 AS image_sha256
               {extra_legal_cols}
        FROM canonical_questions cq
        LEFT JOIN images im ON cq.primary_image_id = im.id
        ORDER BY cq.canonical_id
        """
    )
    q_cols = [d[0] for d in cur.description]
    q_rows = [_row_to_dict(r, q_cols) for r in cur.fetchall()]

    cur.execute(
        """
        SELECT canonical_id, language, question_text, explanation, translation_status
        FROM canonical_translations
        ORDER BY canonical_id, language
        """
    )
    t_cols = [d[0] for d in cur.description]
    translations_by_id: Dict[str, Dict[str, Any]] = {}
    translation_count = 0
    for r in cur.fetchall():
        tr = _row_to_dict(r, t_cols)
        translation_count += 1
        translations_by_id.setdefault(tr["canonical_id"], {})[tr["language"]] = {
            "question_text": tr["question_text"],
            "explanation": tr["explanation"],
            "status": tr["translation_status"],
        }

    cur.execute(
        """
        SELECT canonical_id, option_key, sort_order, is_correct, text_uz_latn, text_uz_cyrl, text_ru
        FROM canonical_answers
        ORDER BY canonical_id, sort_order
        """
    )
    a_cols = [d[0] for d in cur.description]
    answers_by_id: Dict[str, List[Dict[str, Any]]] = {}
    answer_count = 0
    for r in cur.fetchall():
        ar = _row_to_dict(r, a_cols)
        answer_count += 1
        answers_by_id.setdefault(ar["canonical_id"], []).append({
            "key": ar["option_key"],
            "sort_order": ar["sort_order"],
            "is_correct": bool(ar["is_correct"]),
            "text": {
                "uz_latn": ar["text_uz_latn"],
                "uz_cyrl": ar["text_uz_cyrl"],
                "ru": ar["text_ru"],
            },
        })

    cur.execute(
        """
        SELECT COALESCE(cq.category_id, 0) AS category_id, cq.category_name, COUNT(*) AS question_count
        FROM canonical_questions cq
        GROUP BY cq.category_id, cq.category_name
        ORDER BY COALESCE(cq.category_id, 0)
        """
    )
    c_cols = [d[0] for d in cur.description]
    categories = [_row_to_dict(r, c_cols) for r in cur.fetchall()]

    questions_payload: List[Dict[str, Any]] = []
    image_hashes: Dict[str, str] = {}
    for q in q_rows:
        qid = q["canonical_id"]
        providers = parse_source_providers(q.get("source_providers"))
        meta = parse_json_object(q.get("source_metadata"))

        legal_obj: Dict[str, Any] = {
            "reference": q.get("legal_reference"),
            "act_title": q.get("legal_act_title"),
            "verification_status": q.get("verification_status"),
        }
        if extra_legal_cols:
            legal_obj.update({
                "legal_verification_status": q.get("legal_verification_status"),
                "doc_title": q.get("legal_doc_title"),
                "doc_url": q.get("legal_doc_url"),
                "chapter": q.get("legal_chapter"),
                "clause": q.get("legal_clause"),
                "effective_date": q.get("legal_effective_date"),
            })

        img_obj = None
        if q["has_image"]:
            img_obj = {
                "id": q["primary_image_id"],
                "path": q["image_path"],
                "sha256": q["image_sha256"],
            }
            if q.get("image_path") and q.get("image_sha256"):
                image_hashes[str(q["image_path"])] = str(q["image_sha256"])

        item: Dict[str, Any] = {
            "canonical_id": qid,
            "category": {
                "id": q["category_id"],
                "name": q["category_name"],
            },
            "has_image": bool(q["has_image"]),
            "image": img_obj,
            "correct_option_key": q["correct_option_key"],
            "legal": legal_obj,
            "translations": translations_by_id.get(qid, {}),
            "options": answers_by_id.get(qid, []),
        }
        if include_editorial_metadata:
            item.update({
                "deduplication_status": q["deduplication_status"],
                "rights_review_status": q["rights_review_status"],
                "source_providers": providers,
                "source_metadata": meta,
                "created_at": q["created_at"],
                "updated_at": q["updated_at"],
            })
        questions_payload.append(item)

    db_rev = get_db_catalog_revision(conn)
    rev_int = int(db_rev if db_rev is not None else 0)
    now_dt = datetime.now(timezone.utc)
    generated_at = now_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    bundle_version = f"{now_dt.strftime('%Y.%m.%dT%H%M%SZ')}-r{rev_int}-n{len(questions_payload)}"
    payload_sha256 = compute_canonical_payload_sha256(questions_payload)

    bundle = {
        "schema_version": BUNDLE_SCHEMA_VERSION,
        "bundle_version": bundle_version,
        "db_catalog_revision": rev_int,
        "generated_at": generated_at,
        "canonical_count": len(questions_payload),
        "translation_count": translation_count,
        "answer_count": answer_count,
        "payload_sha256": payload_sha256,
        "questions": questions_payload,
        "categories": categories,
    }
    manifest = {
        "schema_version": BUNDLE_SCHEMA_VERSION,
        "bundle_version": bundle_version,
        "db_catalog_revision": rev_int,
        "generated_at": generated_at,
        "canonical_count": len(questions_payload),
        "translation_count": translation_count,
        "answer_count": answer_count,
        "payload_sha256": payload_sha256,
        "image_count": len(image_hashes),
        "image_sha256_refs": image_hashes,
    }
    return bundle, manifest


def _atomic_write_json(target_path: Union[str, Path], payload: Dict[str, Any]) -> int:
    target = Path(target_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = target.with_name(f"{target.name}.tmp.{os.getpid()}")
    serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(serialized)
        f.flush()
        os.fsync(f.fileno())
    # Re-parse verification before swapping into place
    with open(tmp_path, "r", encoding="utf-8") as verify_f:
        parsed = json.load(verify_f)
    if parsed.get("payload_sha256") != payload.get("payload_sha256"):
        os.remove(tmp_path)
        raise ValueError("Atomic bundle write verification failed: SHA-256 mismatch after flush")
    os.replace(tmp_path, target)
    return os.path.getsize(target)


def write_canonical_bundle_atomic(
    db_path_or_conn: Union[str, Path, Any] = "master_database.sqlite",
    out_dir: Union[str, Path] = "data",
    verify_min_count: int = 1295,
    include_editorial_metadata: bool = False,
) -> Dict[str, Any]:
    """
    Atomically builds, SHA-256 verifies, and swaps data/canonical_bundle.json and canonical_bundle.manifest.json.
    """
    owns_conn = isinstance(db_path_or_conn, (str, Path))
    conn = get_db_connection(str(db_path_or_conn)) if owns_conn else db_path_or_conn
    try:
        bundle, manifest = build_canonical_bundle(conn, include_editorial_metadata=include_editorial_metadata)
    finally:
        if owns_conn:
            conn.close()

    if bundle["canonical_count"] < verify_min_count:
        raise ValueError(
            f"Refusing to publish canonical_bundle.json: canonical_count={bundle['canonical_count']} < {verify_min_count}"
        )

    out_path = Path(out_dir)
    bundle_file = out_path / "canonical_bundle.json"
    manifest_file = out_path / "canonical_bundle.manifest.json"

    bundle_bytes = _atomic_write_json(bundle_file, bundle)
    manifest["byte_length"] = bundle_bytes
    _atomic_write_json(manifest_file, manifest)

    return {
        "bundle_path": str(bundle_file),
        "manifest_path": str(manifest_file),
        "bundle_version": bundle["bundle_version"],
        "db_catalog_revision": bundle["db_catalog_revision"],
        "canonical_count": bundle["canonical_count"],
        "translation_count": bundle["translation_count"],
        "answer_count": bundle["answer_count"],
        "payload_sha256": bundle["payload_sha256"],
        "byte_length": bundle_bytes,
    }


def verify_and_load_canonical_bundle(bundle_path: Union[str, Path]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Loads and cryptographically verifies a canonical_bundle.json artifact.
    Returns (bundle, None) if valid, or (None, reason) if missing, malformed, or tampered.
    """
    path = Path(bundle_path)
    if not path.exists():
        return None, "BUNDLE_MISSING"

    try:
        with open(path, "r", encoding="utf-8") as f:
            bundle = json.load(f)
    except Exception as exc:
        return None, f"BUNDLE_JSON_INVALID:{exc}"

    if not isinstance(bundle, dict) or bundle.get("schema_version") != BUNDLE_SCHEMA_VERSION:
        return None, "BUNDLE_SCHEMA_MISMATCH"

    questions = bundle.get("questions")
    categories = bundle.get("categories")
    if not isinstance(questions, list) or not isinstance(categories, list) or not questions:
        return None, "BUNDLE_EMPTY_OR_MALFORMED"

    if bundle.get("canonical_count") != len(questions):
        return None, "BUNDLE_COUNT_MISMATCH"

    expected_sha = bundle.get("payload_sha256")
    actual_sha = compute_canonical_payload_sha256(questions)
    if not expected_sha or expected_sha != actual_sha:
        return None, "BUNDLE_SHA256_MISMATCH"

    return bundle, None


def trigger_vercel_deploy_hook(reason: str = "catalog_updated") -> bool:
    """
    Optional non-blocking Vercel deploy hook trigger when VERCEL_DEPLOY_HOOK_URL is configured.
    Safe no-op when unset.
    """
    hook_url = os.getenv("VERCEL_DEPLOY_HOOK_URL", "").strip()
    if not hook_url:
        return False
    try:
        req = urllib.request.Request(
            hook_url,
            data=json.dumps({"reason": reason}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            return 200 <= resp.status < 300
    except Exception as exc:
        logger.warning("Optional VERCEL_DEPLOY_HOOK_URL trigger failed: %s", exc)
        return False
