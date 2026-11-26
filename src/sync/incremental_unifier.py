"""
Incremental Unification Engine.
Safely ingests newly discovered questions and amends existing questions into master_database.sqlite
WITHOUT modifying existing canonical IDs (CQ-0001..CQ-1295) or breaking user session data.
"""
import os
import sqlite3
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from src.db.catalog_bundle import bump_catalog_version_sql
from src.db.sqlite_utils import backup_sqlite_wal_safe, get_table_columns
from src.db_adapter import execute_batch, get_db_connection, is_turso_enabled
from src.sync.adapters.base_adapter import BaseSourceAdapter, RawQuestion
from src.sync.diff_detector import DiffDetector, QuestionDiffItem, SourceDiffReport
from src.sync.media_sync import MediaSyncPipeline

class IncrementalUnifier:
    def __init__(self, db_path: str = "master_database.sqlite", backup_dir: str = "data/backups"):
        self.db_path = db_path
        self.backup_dir = backup_dir
        try:
            os.makedirs(self.backup_dir, exist_ok=True)
        except OSError:
            pass

    def create_database_backup(self) -> Optional[str]:
        """Creates a WAL-safe snapshot of the local master database before executing sync."""
        if is_turso_enabled() or not os.path.exists(self.db_path):
            return None
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"master_database_pre_sync_{timestamp}.sqlite"
        backup_path = os.path.join(self.backup_dir, backup_filename)
        return backup_sqlite_wal_safe(self.db_path, backup_path, allow_overwrite=False)

    def _get_next_canonical_int(self, conn: sqlite3.Connection) -> int:
        cur = conn.cursor()
        cur.execute("""
            SELECT MAX(CAST(SUBSTR(canonical_id, 4) AS INTEGER))
            FROM canonical_questions
            WHERE canonical_id LIKE 'CQ-%';
        """)
        row = cur.fetchone()
        if row and row[0] is not None:
            return int(row[0]) + 1
        return 1296

    def _get_or_create_category(self, conn: sqlite3.Connection, slug: str, name: str) -> int:
        cur = conn.cursor()
        cur.execute("SELECT id FROM categories WHERE slug = ?;", (slug,))
        row = cur.fetchone()
        if row:
            return row[0]
        cur.execute("INSERT INTO categories (slug, name) VALUES (?, ?);", (slug, name))
        return cur.lastrowid

    def sync_source(
        self,
        adapter: BaseSourceAdapter,
        target_tickets: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        Executes a full incremental sync on the specified source adapter.
        Only ingests new tickets / questions or applies verified amendments.
        """
        backup_path = self.create_database_backup()
        conn = get_db_connection(self.db_path)
        media_pipeline = MediaSyncPipeline(conn)
        detector = DiffDetector(conn)
        source_id = detector.source_id_map.get(adapter.source_code, 1)

        diff_report = detector.inspect_source(adapter)
        tickets_to_process = target_tickets if target_tickets else diff_report.new_tickets

        result_summary = {
            "source_code": adapter.source_code,
            "backup_created": backup_path,
            "tickets_processed": tickets_to_process,
            "new_canonical_questions": 0,
            "new_translations_added": 0,
            "new_images_acquired": 0,
            "amendments_applied": 0,
            "errors": []
        }

        if not tickets_to_process and not diff_report.amended_items:
            conn.close()
            return result_summary

        try:
            cur = conn.cursor()
            next_cq_int = self._get_next_canonical_int(conn)
            cq_cols = get_table_columns(conn, "canonical_questions")
            batch_stmts: List[Any] = []

            # 1. Process New Tickets
            for t_num in tickets_to_process:
                # Fetch all 3 languages for this ticket
                latn_questions = adapter.fetch_ticket(t_num, lang="uz_latn")
                cyrl_questions = {q.position: q for q in adapter.fetch_ticket(t_num, lang="uz_cyrl")}
                ru_questions = {q.position: q for q in adapter.fetch_ticket(t_num, lang="ru")}

                for q_latn in latn_questions:
                    pos = q_latn.position
                    q_cyrl = cyrl_questions.get(pos)
                    q_ru = ru_questions.get(pos)

                    # Category
                    cat_id = self._get_or_create_category(conn, q_latn.category_slug, q_latn.category_name)

                    # Media / Image acquisition
                    image_id = None
                    if q_latn.image_url or q_latn.image_base64:
                        image_id = media_pipeline.process_raw_image(
                            image_url=q_latn.image_url,
                            image_base64=q_latn.image_base64,
                            ref_name=f"{adapter.source_code}_t{t_num}_p{pos}"
                        )
                        if image_id:
                            result_summary["new_images_acquired"] += 1

                    # Canonical ID: CQ-XXXX
                    cq_id = f"CQ-{next_cq_int:04d}"
                    next_cq_int += 1
                    correct_opt_key = chr(ord('A') + q_latn.correct_idx)

                    # Insert canonical question without fabricated legal act claims
                    source_meta = json.dumps({
                        "source": adapter.source_code,
                        "ticket": t_num,
                        "position": pos,
                        "original_id": q_latn.original_id
                    })
                    if "legal_verification_status" in cq_cols:
                        batch_stmts.append((
                            """
                            INSERT INTO canonical_questions (
                                canonical_id, category_id, category_name, primary_image_id, has_image,
                                correct_option_key, legal_reference, legal_act_title, verification_status,
                                legal_verification_status, deduplication_status, source_providers,
                                source_metadata, rights_review_status, created_at, updated_at
                            ) VALUES (?, ?, ?, ?, ?, ?, NULL, NULL, 'SOURCE_CONFIRMED',
                                      'UNRESOLVED_LEGAL_REVIEW', 'CANONICAL_SYNCHRONIZED', ?, ?, 'PUBLIC_ACCESS',
                                      datetime('now'), datetime('now'))
                            """,
                            [cq_id, cat_id, q_latn.category_name, image_id, 1 if image_id else 0,
                             correct_opt_key, adapter.source_code.upper(), source_meta],
                        ))
                    else:
                        batch_stmts.append((
                            """
                            INSERT INTO canonical_questions (
                                canonical_id, category_id, category_name, primary_image_id, has_image,
                                correct_option_key, legal_reference, legal_act_title, verification_status,
                                deduplication_status, source_providers, source_metadata, rights_review_status,
                                created_at, updated_at
                            ) VALUES (?, ?, ?, ?, ?, ?, NULL, NULL, 'SOURCE_CONFIRMED',
                                      'CANONICAL_SYNCHRONIZED', ?, ?, 'PUBLIC_ACCESS',
                                      datetime('now'), datetime('now'))
                            """,
                            [cq_id, cat_id, q_latn.category_name, image_id, 1 if image_id else 0,
                             correct_opt_key, adapter.source_code.upper(), source_meta],
                        ))

                    result_summary["new_canonical_questions"] += 1

                    # Insert canonical translations for all available languages
                    lang_items = [("uz_latn", q_latn)]
                    if q_cyrl:
                        lang_items.append(("uz_cyrl", q_cyrl))
                    if q_ru:
                        lang_items.append(("ru", q_ru))

                    for lang_code, raw_q in lang_items:
                        batch_stmts.append((
                            """
                            INSERT INTO canonical_translations (
                                canonical_id, language, question_text, explanation, translation_status
                            ) VALUES (?, ?, ?, ?, 'ORIGINAL_VERIFIED')
                            """,
                            [cq_id, lang_code, raw_q.question_text, raw_q.explanation],
                        ))
                        result_summary["new_translations_added"] += 1

                    # Insert canonical answers (combining options across languages)
                    max_opts = len(q_latn.options)
                    for opt_idx in range(max_opts):
                        opt_key = chr(ord('A') + opt_idx)
                        is_correct = 1 if opt_idx == q_latn.correct_idx else 0
                        txt_latn = q_latn.options[opt_idx] if opt_idx < len(q_latn.options) else ""
                        txt_cyrl = q_cyrl.options[opt_idx] if (q_cyrl and opt_idx < len(q_cyrl.options)) else txt_latn
                        txt_ru = q_ru.options[opt_idx] if (q_ru and opt_idx < len(q_ru.options)) else txt_latn

                        batch_stmts.append((
                            """
                            INSERT INTO canonical_answers (
                                canonical_id, option_key, sort_order, is_correct,
                                text_uz_latn, text_uz_cyrl, text_ru
                            ) VALUES (?, ?, ?, ?, ?, ?, ?)
                            """,
                            [cq_id, opt_key, opt_idx, is_correct, txt_latn, txt_cyrl, txt_ru],
                        ))

                    # Maintain FK-valid parent questions row before inserting question_sources
                    raw_hash = detector.compute_canonical_hash(q_latn.language, q_latn.question_text, q_latn.options)
                    batch_stmts.append((
                        """
                        INSERT OR IGNORE INTO questions (
                            id, canonical_hash, question_text, category_id, language, image_id,
                            explanation, verification_status, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, 'uz_latn', ?, ?, 'SOURCE_CONFIRMED', datetime('now'), datetime('now'))
                        """,
                        [cq_id, raw_hash, q_latn.question_text, cat_id, image_id, q_latn.explanation],
                    ))
                    batch_stmts.append((
                        """
                        INSERT INTO question_sources (
                            question_id, source_id, original_question_id, original_ticket,
                            original_position, original_url, original_language, collection_timestamp, raw_payload
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), ?)
                        """,
                        [cq_id, source_id, q_latn.original_id, t_num, pos,
                         f"{adapter.base_url}/ticket-{t_num}", "uz_latn", q_latn.raw_payload],
                    ))

                    # Insert audit merge log
                    batch_stmts.append((
                        """
                        INSERT INTO audit_merge_log (
                            canonical_id, operation_type, propdd_slot, yesprava_slot, match_criteria, performed_at
                        ) VALUES (?, 'INCREMENTAL_INGEST', ?, ?, 'AUTOMATED_SYNC', datetime('now'))
                        """,
                        [cq_id,
                         f"t{t_num}_p{pos}" if adapter.source_code == 'propdd' else None,
                         f"t{t_num}_p{pos}" if adapter.source_code == 'yesprava' else None],
                    ))

            # 2. Process Amendments if any
            for amend in diff_report.amended_items:
                if amend.existing_question_id:
                    new_key = chr(ord('A') + amend.new_correct_idx)
                    batch_stmts.append((
                        """
                        UPDATE canonical_questions
                        SET correct_option_key = ?, updated_at = datetime('now')
                        WHERE canonical_id = ?
                        """,
                        [new_key, amend.existing_question_id],
                    ))

                    batch_stmts.append((
                        """
                        UPDATE canonical_answers
                        SET is_correct = (CASE WHEN option_key = ? THEN 1 ELSE 0 END)
                        WHERE canonical_id = ?
                        """,
                        [new_key, amend.existing_question_id],
                    ))

                    result_summary["amendments_applied"] += 1

            if batch_stmts:
                batch_stmts.append(bump_catalog_version_sql())
            execute_batch(conn, batch_stmts)
        except Exception as e:
            conn.rollback()
            result_summary["errors"].append(str(e))
        finally:
            conn.close()

        return result_summary
