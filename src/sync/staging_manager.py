"""
Staging & Human-in-the-Loop Moderation Manager.
Ensures external questions are placed in a quarantined review queue first.
Nothing enters the production canonical database until the administrator inspects and approves it.
"""
import os
import json
import sqlite3
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from src.db.catalog_bundle import bump_catalog_version_sql
from src.db.provenance_classifier import ALLOWED_VERIFIED_STATUSES
from src.db.sqlite_utils import backup_sqlite_wal_safe, get_table_columns
from src.db_adapter import execute_batch, is_turso_enabled
from src.sync.adapters.base_adapter import BaseSourceAdapter, RawQuestion
from src.sync.diff_detector import QuestionDiffItem
from src.sync.media_sync import MediaSyncPipeline

class StagingManager:
    def __init__(self, db_path: Optional[str] = None, backup_dir: str = "data/backups"):
        self.db_path = db_path or os.getenv("DB_PATH", "master_database.sqlite")
        self.backup_dir = backup_dir
        try:
            os.makedirs(self.backup_dir, exist_ok=True)
        except OSError:
            pass

    def _get_connection(self):
        from src.db_adapter import get_db_connection
        return get_db_connection(self.db_path)

    def create_database_backup(self) -> Optional[str]:
        if is_turso_enabled() or not os.path.exists(self.db_path):
            return None
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"master_database_pre_approval_{timestamp}.sqlite"
        backup_path = os.path.join(self.backup_dir, backup_filename)
        return backup_sqlite_wal_safe(self.db_path, backup_path, allow_overwrite=False)

    def stage_diff_items(
        self,
        source_code: str,
        adapter: BaseSourceAdapter,
        diff_items: List[QuestionDiffItem]
    ) -> int:
        """
        Takes detected diff items from a source and stores them in staged_questions
        for human admin review. Does NOT touch canonical tables.
        """
        if not diff_items:
            return 0

        conn = self._get_connection()
        media_pipeline = MediaSyncPipeline(conn)
        staged_count = 0

        try:
            cur = conn.cursor()

            # Group items by ticket to minimize API calls
            tickets_to_fetch = sorted(list(set(item.ticket_num for item in diff_items)))
            ticket_data_cache: Dict[int, Dict[str, List[RawQuestion]]] = {}

            for t_num in tickets_to_fetch:
                ticket_data_cache[t_num] = {
                    "uz_latn": adapter.fetch_ticket(t_num, lang="uz_latn"),
                    "uz_cyrl": adapter.fetch_ticket(t_num, lang="uz_cyrl"),
                    "ru": adapter.fetch_ticket(t_num, lang="ru")
                }

            for item in diff_items:
                t_num = item.ticket_num
                pos = item.position

                # Check if already staged or approved
                cur.execute("""
                    SELECT id FROM staged_questions
                    WHERE source_code = ? AND source_ticket = ? AND source_position = ? AND review_status IN ('PENDING_REVIEW', 'APPROVED');
                """, (source_code, t_num, pos))
                if cur.fetchone():
                    continue  # Already in review queue or approved

                # Check if already in canonical database
                s_id = 1 if source_code.lower() == 'yesprava' else 2
                cur.execute("""
                    SELECT question_id FROM question_sources
                    WHERE source_id = ? AND original_ticket = ? AND original_position = ? LIMIT 1;
                """, (s_id, t_num, pos))
                if cur.fetchone():
                    continue  # Already published into canonical database

                t_cache = ticket_data_cache.get(t_num, {})
                q_latn = next((q for q in t_cache.get("uz_latn", []) if q.position == pos), item.raw_item)
                q_cyrl = next((q for q in t_cache.get("uz_cyrl", []) if q.position == pos), None)
                q_ru = next((q for q in t_cache.get("ru", []) if q.position == pos), None)

                if not q_latn:
                    continue

                # Stage image if present
                staged_image_id = None
                img_url = q_latn.image_url
                if q_latn.image_url or q_latn.image_base64:
                    staged_image_id = media_pipeline.process_raw_image(
                        image_url=q_latn.image_url,
                        image_base64=q_latn.image_base64,
                        ref_name=f"staged_{source_code}_t{t_num}_p{pos}"
                    )

                # Build multi-lingual options JSON
                options_list = []
                max_opts = len(q_latn.options)
                for opt_idx in range(max_opts):
                    opt_key = chr(ord('A') + opt_idx)
                    is_corr = 1 if opt_idx == q_latn.correct_idx else 0
                    txt_latn = q_latn.options[opt_idx] if opt_idx < len(q_latn.options) else ""
                    txt_cyrl = q_cyrl.options[opt_idx] if (q_cyrl and opt_idx < len(q_cyrl.options)) else txt_latn
                    txt_ru = q_ru.options[opt_idx] if (q_ru and opt_idx < len(q_ru.options)) else txt_latn

                    options_list.append({
                        "key": opt_key,
                        "sort_order": opt_idx,
                        "is_correct": is_corr,
                        "text_uz_latn": txt_latn,
                        "text_uz_cyrl": txt_cyrl,
                        "text_ru": txt_ru
                    })

                correct_key = chr(ord('A') + q_latn.correct_idx)
                raw_payload = q_latn.raw_payload or json.dumps({"source": source_code, "ticket": t_num, "pos": pos})

                cur.execute("""
                    INSERT INTO staged_questions (
                        source_code, source_ticket, source_position, change_type, existing_canonical_id,
                        category_slug, category_name, image_url, staged_image_id,
                        text_uz_latn, text_uz_cyrl, text_ru,
                        options_json, correct_option_key, explanation, raw_payload,
                        review_status, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING_REVIEW', datetime('now'), datetime('now'));
                """, (
                    source_code, t_num, pos, item.diff_type, item.existing_question_id,
                    q_latn.category_slug, q_latn.category_name, img_url, staged_image_id,
                    q_latn.question_text,
                    q_cyrl.question_text if q_cyrl else q_latn.question_text,
                    q_ru.question_text if q_ru else q_latn.question_text,
                    json.dumps(options_list, ensure_ascii=False),
                    correct_key,
                    q_latn.explanation,
                    raw_payload
                ))
                staged_count += 1

            conn.commit()
            return staged_count
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def get_pending_count(self) -> int:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM staged_questions WHERE review_status = 'PENDING_REVIEW';")
            return cur.fetchone()[0]

    def list_staged_questions(self, status: str = "PENDING_REVIEW", limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT sq.*, im.local_path as image_local_path, im.filename as image_filename
                FROM staged_questions sq
                LEFT JOIN images im ON sq.staged_image_id = im.id
                WHERE sq.review_status = ?
                ORDER BY sq.id ASC
                LIMIT ? OFFSET ?;
            """, (status, limit, offset))
            rows = cur.fetchall()

            results = []
            for r in rows:
                row_dict = dict(r)
                try:
                    row_dict["options"] = json.loads(row_dict.get("options_json") or "[]")
                except Exception:
                    row_dict["options"] = []

                if row_dict.get("image_filename"):
                    row_dict["image_src"] = f"/images/{row_dict['image_filename']}"
                elif row_dict.get("image_url"):
                    row_dict["image_src"] = row_dict["image_url"]
                else:
                    row_dict["image_src"] = None

                results.append(row_dict)
            return results

    def approve_question(
        self,
        staged_id: int,
        admin_username: str = "Admin",
        editorial_meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Approves a staged question and atomically publishes it into the production canonical catalog.
        Optionally attaches classified legal provenance and per-language explanations inside the same batch.
        """
        meta_in = editorial_meta or {}
        legal_status = (meta_in.get("legal_verification_status") or "UNRESOLVED_LEGAL_REVIEW").strip()
        if legal_status not in ALLOWED_VERIFIED_STATUSES:
            raise ValueError(f"Invalid legal_verification_status: {legal_status}")

        legal_doc_title = (meta_in.get("legal_doc_title") or "").strip() or None
        legal_doc_url = (meta_in.get("legal_doc_url") or "").strip() or None
        legal_chapter = (meta_in.get("legal_chapter") or "").strip() or None
        legal_clause = (meta_in.get("legal_clause") or "").strip() or None
        legal_effective_date = (meta_in.get("legal_effective_date") or "").strip() or None

        if legal_status == "VERIFIED_PRIMARY_LAW" and (
            not legal_doc_title or not (legal_chapter or legal_clause)
        ):
            raise ValueError(
                "VERIFIED_PRIMARY_LAW requires non-empty legal_doc_title and legal_chapter or legal_clause."
            )

        combined_ref = " — ".join(p for p in (legal_chapter, legal_clause) if p) or None
        backup_path = self.create_database_backup()
        conn = self._get_connection()

        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM staged_questions WHERE id = ?;", (staged_id,))
            staged = cur.fetchone()
            if not staged:
                raise ValueError(f"Staged question #{staged_id} not found.")

            if staged["review_status"] == "APPROVED":
                return {"success": True, "already_approved": True, "canonical_id": staged["published_canonical_id"]}

            options = json.loads(staged["options_json"] or "[]")

            # Check if this is an AMENDMENT to an existing canonical question
            existing_cq_id = None
            if staged["change_type"] == "AMENDMENT":
                # 1. By direct existing_canonical_id
                if staged["existing_canonical_id"]:
                    cur.execute("SELECT canonical_id FROM canonical_questions WHERE canonical_id = ?", (staged["existing_canonical_id"],))
                    r = cur.fetchone()
                    if r:
                        existing_cq_id = r[0]

                # 2. By slot match in audit_merge_log
                if not existing_cq_id and staged["source_ticket"] and staged["source_position"]:
                    s_code = staged["source_code"].lower()
                    slot_t_colon = f"T{staged['source_ticket']}:P{staged['source_position']}"
                    slot_t_under = f"t{staged['source_ticket']}_p{staged['source_position']}"
                    if s_code == "propdd":
                        cur.execute("SELECT canonical_id FROM audit_merge_log WHERE propdd_slot IN (?, ?) LIMIT 1", (slot_t_colon, slot_t_under))
                    elif s_code == "yesprava":
                        cur.execute("SELECT canonical_id FROM audit_merge_log WHERE yesprava_slot IN (?, ?) LIMIT 1", (slot_t_colon, slot_t_under))
                    r = cur.fetchone()
                    if r:
                        existing_cq_id = r[0]

                # 3. By question text in canonical_translations
                if not existing_cq_id and staged["text_uz_latn"]:
                    cur.execute("SELECT canonical_id FROM canonical_translations WHERE language = 'uz_latn' AND question_text = ? LIMIT 1", (staged["text_uz_latn"],))
                    r = cur.fetchone()
                    if r:
                        existing_cq_id = r[0]

            if existing_cq_id:
                # Apply amendment atomically via execute_batch()
                new_key = staged["correct_option_key"]
                amend_stmts: List[Any] = [
                    (
                        """
                        UPDATE canonical_questions
                        SET correct_option_key = ?, updated_at = datetime('now')
                        WHERE canonical_id = ?
                        """,
                        [new_key, existing_cq_id],
                    ),
                    (
                        """
                        UPDATE canonical_answers
                        SET is_correct = CASE WHEN option_key = ? THEN 1 ELSE 0 END
                        WHERE canonical_id = ?
                        """,
                        [new_key, existing_cq_id],
                    ),
                ]
                if staged["explanation"]:
                    amend_stmts.append((
                        """
                        UPDATE canonical_translations
                        SET explanation = ?, translation_status = 'ADMIN_VERIFIED'
                        WHERE canonical_id = ?
                        """,
                        [staged["explanation"], existing_cq_id],
                    ))
                amend_stmts.append((
                    """
                    INSERT INTO audit_merge_log (
                        canonical_id, operation_type, propdd_slot, yesprava_slot, match_criteria, performed_at
                    ) VALUES (?, 'ADMIN_AMENDMENT_APPROVAL', ?, ?, 'MANUAL_HUMAN_APPROVAL', datetime('now'))
                    """,
                    [
                        existing_cq_id,
                        f"T{staged['source_ticket']}:P{staged['source_position']}" if staged['source_code'] == 'propdd' else None,
                        f"T{staged['source_ticket']}:P{staged['source_position']}" if staged['source_code'] == 'yesprava' else None,
                    ],
                ))
                amend_stmts.append((
                    """
                    UPDATE staged_questions
                    SET review_status = 'APPROVED',
                        reviewed_by = ?,
                        reviewed_at = datetime('now'),
                        published_canonical_id = ?,
                        updated_at = datetime('now')
                    WHERE id = ?
                    """,
                    [admin_username, existing_cq_id, staged_id],
                ))
                amend_stmts.append(bump_catalog_version_sql())
                execute_batch(conn, amend_stmts)
                return {
                    "success": True,
                    "action": "AMENDMENT_APPLIED",
                    "canonical_id": existing_cq_id,
                    "backup_path": backup_path
                }

            # If NEW_QUESTION or unmatched amendment:
            # 1. Category
            cur.execute("SELECT id FROM categories WHERE slug = ?;", (staged["category_slug"],))
            cat_row = cur.fetchone()
            if cat_row:
                cat_id = cat_row[0]
            else:
                cur.execute("INSERT INTO categories (slug, name) VALUES (?, ?);", (staged["category_slug"], staged["category_name"]))
                conn.commit()
                cat_id = cur.lastrowid

            # 2. Next canonical ID
            cur.execute("""
                SELECT MAX(CAST(SUBSTR(canonical_id, 4) AS INTEGER))
                FROM canonical_questions
                WHERE canonical_id LIKE 'CQ-%';
            """)
            max_row = cur.fetchone()
            next_int = (int(max_row[0]) + 1) if (max_row and max_row[0] is not None) else 1296
            cq_id = f"CQ-{next_int:04d}"

            source_meta = json.dumps({
                "source": staged["source_code"],
                "ticket": staged["source_ticket"],
                "position": staged["source_position"],
                "staged_id": staged_id,
                "approved_by": admin_username,
                "approved_at": datetime.now().isoformat()
            })

            cq_cols = get_table_columns(conn, "canonical_questions")
            cur.execute("SELECT id FROM sources WHERE source_code = ?;", (staged["source_code"],))
            s_row = cur.fetchone()
            s_id = s_row[0] if s_row else 1

            publish_stmts: List[Any] = []

            # 3. Insert Canonical Question (never invent legal_act_title when legal_reference is NULL)
            reviewed_by = admin_username if legal_status != "UNRESOLVED_LEGAL_REVIEW" else None
            reviewed_at_val = datetime.utcnow().isoformat() if reviewed_by else None
            if {"legal_verification_status", "legal_doc_title", "legal_chapter", "legal_clause"}.issubset(cq_cols):
                publish_stmts.append((
                    """
                    INSERT INTO canonical_questions (
                        canonical_id, category_id, category_name, primary_image_id, has_image,
                        correct_option_key, legal_reference, legal_act_title, verification_status,
                        legal_verification_status, legal_doc_title, legal_doc_url,
                        legal_chapter, legal_clause, legal_effective_date,
                        editorial_reviewed_by, editorial_reviewed_at,
                        deduplication_status, source_providers,
                        source_metadata, rights_review_status, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'ADMIN_MANUALLY_APPROVED',
                              ?, ?, ?, ?, ?, ?, ?, ?, 'CANONICAL_SYNCHRONIZED', ?, ?, 'PUBLIC_ACCESS',
                              datetime('now'), datetime('now'))
                    """,
                    [
                        cq_id, cat_id, staged["category_name"], staged["staged_image_id"],
                        1 if staged["staged_image_id"] else 0,
                        staged["correct_option_key"],
                        combined_ref,
                        legal_doc_title,
                        legal_status,
                        legal_doc_title,
                        legal_doc_url,
                        legal_chapter,
                        legal_clause,
                        legal_effective_date,
                        reviewed_by,
                        reviewed_at_val,
                        json.dumps([staged["source_code"].upper()]),
                        source_meta,
                    ],
                ))
            elif "legal_verification_status" in cq_cols:
                publish_stmts.append((
                    """
                    INSERT INTO canonical_questions (
                        canonical_id, category_id, category_name, primary_image_id, has_image,
                        correct_option_key, legal_reference, legal_act_title, verification_status,
                        legal_verification_status, deduplication_status, source_providers,
                        source_metadata, rights_review_status, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'ADMIN_MANUALLY_APPROVED',
                              ?, 'CANONICAL_SYNCHRONIZED', ?, ?, 'PUBLIC_ACCESS',
                              datetime('now'), datetime('now'))
                    """,
                    [
                        cq_id, cat_id, staged["category_name"], staged["staged_image_id"],
                        1 if staged["staged_image_id"] else 0,
                        staged["correct_option_key"],
                        combined_ref,
                        legal_doc_title,
                        legal_status,
                        json.dumps([staged["source_code"].upper()]),
                        source_meta,
                    ],
                ))
            else:
                publish_stmts.append((
                    """
                    INSERT INTO canonical_questions (
                        canonical_id, category_id, category_name, primary_image_id, has_image,
                        correct_option_key, legal_reference, legal_act_title, verification_status,
                        deduplication_status, source_providers, source_metadata, rights_review_status,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'ADMIN_MANUALLY_APPROVED',
                              'CANONICAL_SYNCHRONIZED', ?, ?, 'PUBLIC_ACCESS',
                              datetime('now'), datetime('now'))
                    """,
                    [
                        cq_id, cat_id, staged["category_name"], staged["staged_image_id"],
                        1 if staged["staged_image_id"] else 0,
                        staged["correct_option_key"],
                        combined_ref,
                        legal_doc_title,
                        json.dumps([staged["source_code"].upper()]),
                        source_meta,
                    ],
                ))

            # 4. Insert Translations (supporting per-language admin explanations)
            expl_latn = (meta_in.get("explanation_uz_latn") or "").strip() or staged["explanation"]
            expl_cyrl = (meta_in.get("explanation_uz_cyrl") or "").strip() or staged["explanation"]
            expl_ru = (meta_in.get("explanation_ru") or "").strip() or staged["explanation"]

            publish_stmts.append((
                """
                INSERT INTO canonical_translations (canonical_id, language, question_text, explanation, translation_status)
                VALUES (?, 'uz_latn', ?, ?, 'ADMIN_VERIFIED')
                """,
                [cq_id, staged["text_uz_latn"], expl_latn],
            ))

            if staged["text_uz_cyrl"]:
                publish_stmts.append((
                    """
                    INSERT INTO canonical_translations (canonical_id, language, question_text, explanation, translation_status)
                    VALUES (?, 'uz_cyrl', ?, ?, 'ADMIN_VERIFIED')
                    """,
                    [cq_id, staged["text_uz_cyrl"], expl_cyrl],
                ))

            if staged["text_ru"]:
                publish_stmts.append((
                    """
                    INSERT INTO canonical_translations (canonical_id, language, question_text, explanation, translation_status)
                    VALUES (?, 'ru', ?, ?, 'ADMIN_VERIFIED')
                    """,
                    [cq_id, staged["text_ru"], expl_ru],
                ))

            # 5. Insert Canonical Answers
            for opt in options:
                publish_stmts.append((
                    """
                    INSERT INTO canonical_answers (
                        canonical_id, option_key, sort_order, is_correct,
                        text_uz_latn, text_uz_cyrl, text_ru
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        cq_id, opt["key"], opt.get("sort_order", 0), opt.get("is_correct", 0),
                        opt.get("text_uz_latn", ""),
                        opt.get("text_uz_cyrl", opt.get("text_uz_latn", "")),
                        opt.get("text_ru", opt.get("text_uz_latn", "")),
                    ],
                ))

            # 6. Source Trace & Audit Log
            raw_hash = f"staged_{staged_id}_{cq_id}"
            publish_stmts.append((
                """
                INSERT OR IGNORE INTO questions (
                    id, canonical_hash, question_text, category_id, language, image_id,
                    explanation, verification_status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, 'uz_latn', ?, ?, 'ADMIN_APPROVED', datetime('now'), datetime('now'))
                """,
                [cq_id, raw_hash, staged["text_uz_latn"], cat_id, staged["staged_image_id"], staged["explanation"]],
            ))

            publish_stmts.append((
                """
                INSERT INTO question_sources (
                    question_id, source_id, original_question_id, original_ticket,
                    original_position, original_url, original_language, collection_timestamp, raw_payload
                ) VALUES (?, ?, ?, ?, ?, ?, 'uz_latn', datetime('now'), ?)
                """,
                [
                    cq_id, s_id, f"STAGED_{staged_id}", staged["source_ticket"],
                    staged["source_position"], f"https://{staged['source_code']}.uz", staged["raw_payload"],
                ],
            ))

            publish_stmts.append((
                """
                INSERT INTO audit_merge_log (
                    canonical_id, operation_type, propdd_slot, yesprava_slot, match_criteria, performed_at
                ) VALUES (?, 'ADMIN_STAGING_APPROVAL', ?, ?, 'MANUAL_HUMAN_APPROVAL', datetime('now'))
                """,
                [
                    cq_id,
                    f"t{staged['source_ticket']}_p{staged['source_position']}" if staged['source_code'] == 'propdd' else None,
                    f"t{staged['source_ticket']}_p{staged['source_position']}" if staged['source_code'] == 'yesprava' else None,
                ],
            ))

            # 7. Update Staged Question Status & bump catalog_version atomically
            publish_stmts.append((
                """
                UPDATE staged_questions
                SET review_status = 'APPROVED',
                    reviewed_by = ?,
                    reviewed_at = datetime('now'),
                    published_canonical_id = ?,
                    updated_at = datetime('now')
                WHERE id = ?
                """,
                [admin_username, cq_id, staged_id],
            ))
            publish_stmts.append(bump_catalog_version_sql())

            execute_batch(conn, publish_stmts)
            return {
                "success": True,
                "canonical_id": cq_id,
                "backup_path": backup_path
            }
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def reject_question(self, staged_id: int, reason: str = "Rad etildi", admin_username: str = "Admin") -> bool:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE staged_questions
                SET review_status = 'REJECTED',
                    reviewer_notes = ?,
                    reviewed_by = ?,
                    reviewed_at = datetime('now'),
                    updated_at = datetime('now')
                WHERE id = ?;
            """, (reason, admin_username, staged_id))
            conn.commit()
            return cur.rowcount > 0

    def edit_and_approve_question(
        self,
        staged_id: int,
        edited_data: Dict[str, Any],
        admin_username: str = "Admin"
    ) -> Dict[str, Any]:
        """
        Applies admin edits to the staged question, validates legal provenance metadata,
        and immediately approves and publishes it atomically.
        """
        legal_status = (edited_data.get("legal_verification_status") or "UNRESOLVED_LEGAL_REVIEW").strip()
        if legal_status not in ALLOWED_VERIFIED_STATUSES:
            raise ValueError(f"Invalid legal_verification_status: {legal_status}")
        if legal_status == "VERIFIED_PRIMARY_LAW" and (
            not (edited_data.get("legal_doc_title") or "").strip()
            or not ((edited_data.get("legal_chapter") or "").strip() or (edited_data.get("legal_clause") or "").strip())
        ):
            raise ValueError(
                "VERIFIED_PRIMARY_LAW requires non-empty legal_doc_title and legal_chapter or legal_clause."
            )

        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE staged_questions
                SET text_uz_latn = COALESCE(?, text_uz_latn),
                    text_uz_cyrl = COALESCE(?, text_uz_cyrl),
                    text_ru = COALESCE(?, text_ru),
                    options_json = COALESCE(?, options_json),
                    correct_option_key = COALESCE(?, correct_option_key),
                    explanation = COALESCE(?, explanation),
                    reviewer_notes = 'ADMIN_EDITED',
                    updated_at = datetime('now')
                WHERE id = ?;
            """, (
                edited_data.get("text_uz_latn"),
                edited_data.get("text_uz_cyrl"),
                edited_data.get("text_ru"),
                json.dumps(edited_data["options"], ensure_ascii=False) if "options" in edited_data else None,
                edited_data.get("correct_option_key"),
                edited_data.get("explanation") or edited_data.get("explanation_uz_latn"),
                staged_id
            ))
            conn.commit()

        return self.approve_question(staged_id, admin_username=admin_username, editorial_meta=edited_data)

    def approve_all_pending(self, admin_username: str = "Admin") -> Dict[str, Any]:
        """Approves all currently pending questions in the review queue."""
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM staged_questions WHERE review_status = 'PENDING_REVIEW' ORDER BY id ASC;")
            ids = [r[0] for r in cur.fetchall()]

        approved = []
        errors = []
        for s_id in ids:
            try:
                res = self.approve_question(s_id, admin_username=admin_username)
                approved.append({"staged_id": s_id, "canonical_id": res["canonical_id"]})
            except Exception as e:
                errors.append({"staged_id": s_id, "error": str(e)})

        return {
            "total_pending": len(ids),
            "approved_count": len(approved),
            "approved": approved,
            "errors": errors
        }
