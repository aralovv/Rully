"""
Question Sync Orchestrator Service.
Coordinates source adapters, diff detection, media pipeline, staging queue,
and administrator Telegram review notifications.
"""
import os
import sqlite3
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime

from src.sync.adapters import BaseSourceAdapter, YesPravaAdapter, ProPDDAdapter, SourceStatus
from src.sync.diff_detector import DiffDetector, SourceDiffReport
from src.sync.incremental_unifier import IncrementalUnifier
from src.sync.staging_manager import StagingManager
from src.security.telegram_notifier import send_telegram_message, MAIN_BOT_TOKEN, ADMIN_TELEGRAM_ID

class QuestionSyncService:
    def __init__(self, db_path: str = "master_database.sqlite"):
        self.db_path = db_path
        self.adapters: Dict[str, BaseSourceAdapter] = {
            "yesprava": YesPravaAdapter(),
            "propdd": ProPDDAdapter()
        }
        self.unifier = IncrementalUnifier(db_path=db_path)
        self.staging = StagingManager(db_path=db_path)

    def get_database_metrics(self) -> Dict[str, int]:
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM canonical_questions;")
        cq_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM canonical_translations;")
        ct_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM images;")
        img_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(DISTINCT original_ticket) FROM question_sources WHERE original_ticket IS NOT NULL;")
        tickets_count = cur.fetchone()[0]

        try:
            cur.execute("SELECT COUNT(*) FROM staged_questions WHERE review_status = 'PENDING_REVIEW';")
            staged_count = cur.fetchone()[0]
        except Exception:
            staged_count = 0

        conn.close()
        return {
            "canonical_questions": cq_count,
            "canonical_translations": ct_count,
            "total_images": img_count,
            "total_tickets": tickets_count,
            "pending_staged_reviews": staged_count
        }

    def get_all_source_statuses(self) -> List[Dict[str, Any]]:
        results = []
        for code, adapter in self.adapters.items():
            st = adapter.check_status()
            results.append({
                "source_code": st.source_code,
                "source_name": st.source_name,
                "source_url": st.source_url,
                "is_online": st.is_online,
                "response_time_ms": st.response_time_ms,
                "tickets_count": st.tickets_count,
                "estimated_questions": st.estimated_questions_count,
                "last_checked": st.last_checked,
                "error": st.error_message
            })
        return results

    def check_for_updates(self, sample_limit: Optional[int] = 2, auto_stage: bool = True) -> Dict[str, Any]:
        """
        Inspects external sources for changes.
        If changes are found and auto_stage is True, stages them into the review queue.
        Does NOT publish to production canonical catalog.
        """
        conn = sqlite3.connect(self.db_path)
        detector = DiffDetector(conn)
        reports = []
        total_new_questions = 0
        total_amendments = 0
        new_tickets_found = []
        total_staged_now = 0

        for code, adapter in self.adapters.items():
            rep = detector.inspect_source(adapter, sample_limit=sample_limit)
            total_new_questions += rep.new_questions_count
            total_amendments += rep.amended_questions_count
            if rep.new_tickets:
                new_tickets_found.extend([f"{code}: Bilet {t}" for t in rep.new_tickets])

            # Auto-stage into review queue
            if auto_stage and (rep.new_items or rep.amended_items):
                try:
                    staged_n = self.staging.stage_diff_items(code, adapter, rep.new_items + rep.amended_items)
                    total_staged_now += staged_n
                except Exception as e:
                    pass

            reports.append({
                "source_code": rep.source_code,
                "source_name": rep.source_name,
                "checked_at": rep.checked_at,
                "total_tickets_online": rep.total_tickets_online,
                "new_tickets": rep.new_tickets,
                "new_questions_count": rep.new_questions_count,
                "amended_questions_count": rep.amended_questions_count,
                "unchanged_questions_count": rep.unchanged_questions_count,
                "has_changes": rep.has_changes
            })

        conn.close()

        has_updates = (total_new_questions > 0 or total_amendments > 0 or len(new_tickets_found) > 0)
        pending_total = self.staging.get_pending_count()

        if has_updates and total_staged_now > 0:
            self._notify_admin_of_staging(total_staged_now, pending_total)

        return {
            "has_updates": has_updates,
            "total_new_questions": total_new_questions,
            "total_amendments": total_amendments,
            "new_tickets": new_tickets_found,
            "newly_staged_count": total_staged_now,
            "total_pending_review": pending_total,
            "source_reports": reports,
            "db_metrics": self.get_database_metrics()
        }

    def _notify_admin_of_staging(self, newly_staged: int, total_pending: int):
        """Notifies admin that new questions arrived in the staging review queue."""
        msg = (
            "📋 <b>Avtotest: Yangi Savollar Tekshiruvga Tayyor!</b>\n\n"
            f"Yangi kelgan savollar: <b>+{newly_staged} ta</b>\n"
            f"Moderatsiyada kutilmoqda: <b>{total_pending} ta</b>\n\n"
            "⚠️ <i>Savollar to‘g‘riligini tekshirib, tasdiqlaguningizcha asosiy foydalanuvchilar bazasiga qo‘shilmaydi.</i>\n\n"
            "Tekshirish uchun: Admin Panel → Sozlamalar → <b>Nazariy Savollar & Moderatsiya</b>"
        )
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(send_telegram_message(MAIN_BOT_TOKEN, ADMIN_TELEGRAM_ID, msg))
            else:
                loop.run_until_complete(send_telegram_message(MAIN_BOT_TOKEN, ADMIN_TELEGRAM_ID, msg))
        except Exception:
            pass
