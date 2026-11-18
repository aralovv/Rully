"""
Diff & Change Detection Engine for Driving Theory Questions.
Detects new tickets, new questions, and answer key amendments against master_database.sqlite.
"""
import hashlib
import sqlite3
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from src.sync.adapters.base_adapter import BaseSourceAdapter, RawQuestion

@dataclass
class QuestionDiffItem:
    diff_type: str  # NEW_QUESTION, AMENDMENT, IMAGE_UPDATE, UNCHANGED
    source_code: str
    ticket_num: int
    position: int
    language: str
    question_text: str
    canonical_hash: str
    existing_question_id: Optional[str] = None
    old_correct_idx: Optional[int] = None
    new_correct_idx: Optional[int] = None
    has_image: bool = False
    raw_item: Optional[RawQuestion] = None

@dataclass
class SourceDiffReport:
    source_code: str
    source_name: str
    checked_at: str
    total_tickets_online: int
    new_tickets: List[int]
    total_questions_scanned: int
    new_questions_count: int
    amended_questions_count: int
    unchanged_questions_count: int
    new_items: List[QuestionDiffItem] = field(default_factory=list)
    amended_items: List[QuestionDiffItem] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return self.new_questions_count > 0 or self.amended_questions_count > 0 or len(self.new_tickets) > 0

class DiffDetector:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.known_hashes: Set[str] = set()
        self.known_source_slots: Set[Tuple[int, int, int]] = set()  # (source_id, ticket, pos)
        self.source_id_map: Dict[str, int] = {}
        self._populate_known_index()

    def _populate_known_index(self):
        cur = self.conn.cursor()
        # 1. Map source codes to ids
        cur.execute("SELECT id, source_code FROM sources;")
        for row in cur.fetchall():
            self.source_id_map[row[1]] = row[0]

        # 2. Known canonical hashes in questions
        cur.execute("SELECT canonical_hash FROM questions WHERE canonical_hash IS NOT NULL;")
        for row in cur.fetchall():
            self.known_hashes.add(row[0])

        # 3. Known source slots in question_sources
        cur.execute("""
            SELECT source_id, original_ticket, original_position
            FROM question_sources
            WHERE original_ticket IS NOT NULL AND original_position IS NOT NULL;
        """)
        for row in cur.fetchall():
            try:
                self.known_source_slots.add((int(row[0]), int(row[1]), int(row[2])))
            except (ValueError, TypeError):
                pass

    @staticmethod
    def compute_canonical_hash(lang: str, text: str, options: List[str]) -> str:
        norm_text = " ".join(text.lower().split())
        norm_opts = "|".join(" ".join(opt.lower().split()) for opt in options)
        hash_input = f"{lang}:{norm_text}:{norm_opts}".encode("utf-8")
        return hashlib.sha256(hash_input).hexdigest()

    def inspect_source(
        self,
        adapter: BaseSourceAdapter,
        sample_limit: Optional[int] = None
    ) -> SourceDiffReport:
        source_id = self.source_id_map.get(adapter.source_code, 1)
        cur = self.conn.cursor()

        # Find existing max ticket for this source
        cur.execute("""
            SELECT MAX(CAST(original_ticket AS INTEGER))
            FROM question_sources
            WHERE source_id = ?;
        """, (source_id,))
        row = cur.fetchone()
        max_existing_ticket = row[0] if (row and row[0]) else 0

        # Discover all online tickets
        online_tickets = adapter.discover_tickets()
        new_tickets = [t for t in online_tickets if t > max_existing_ticket]

        report = SourceDiffReport(
            source_code=adapter.source_code,
            source_name=adapter.source_name,
            checked_at=datetime.now().isoformat(),
            total_tickets_online=len(online_tickets),
            new_tickets=new_tickets,
            total_questions_scanned=0,
            new_questions_count=0,
            amended_questions_count=0,
            unchanged_questions_count=0
        )

        # Check tickets: prioritize new tickets first, plus audit existing tickets
        tickets_to_check = new_tickets if new_tickets else online_tickets
        if sample_limit and not new_tickets:
            # If no new tickets, check the latest 5 tickets to verify amendments
            tickets_to_check = sorted(online_tickets)[-sample_limit:]

        for t_num in tickets_to_check:
            for lang in ["uz_latn"]:  # Check base language first for rapid detection
                if adapter.source_code == 'propdd':
                    questions = adapter.fetch_ticket(t_num, lang=lang, download_images=False)
                else:
                    questions = adapter.fetch_ticket(t_num, lang=lang)
                for q in questions:
                    report.total_questions_scanned += 1
                    c_hash = self.compute_canonical_hash(q.language, q.question_text, q.options)
                    slot = (source_id, q.ticket_num, q.position)

                    is_known_hash = c_hash in self.known_hashes
                    is_known_slot = slot in self.known_source_slots

                    if not is_known_hash and not is_known_slot:
                        # Brand new question
                        diff_item = QuestionDiffItem(
                            diff_type="NEW_QUESTION",
                            source_code=adapter.source_code,
                            ticket_num=q.ticket_num,
                            position=q.position,
                            language=q.language,
                            question_text=q.question_text,
                            canonical_hash=c_hash,
                            has_image=bool(q.image_url or q.image_base64),
                            raw_item=q
                        )
                        report.new_questions_count += 1
                        report.new_items.append(diff_item)
                    elif is_known_slot:
                        # Slot known, let's verify if answer changed
                        cur.execute("""
                            SELECT q.id, a.sort_order
                            FROM question_sources qs
                            JOIN questions q ON qs.question_id = q.id
                            JOIN answers a ON q.id = a.question_id AND a.is_correct = 1
                            WHERE qs.source_id = ? AND qs.original_ticket = ? AND qs.original_position = ?
                            LIMIT 1;
                        """, (source_id, q.ticket_num, q.position))
                        existing_row = cur.fetchone()
                        if existing_row and existing_row[1] != q.correct_idx:
                            diff_item = QuestionDiffItem(
                                diff_type="AMENDMENT",
                                source_code=adapter.source_code,
                                ticket_num=q.ticket_num,
                                position=q.position,
                                language=q.language,
                                question_text=q.question_text,
                                canonical_hash=c_hash,
                                existing_question_id=existing_row[0],
                                old_correct_idx=existing_row[1],
                                new_correct_idx=q.correct_idx,
                                raw_item=q
                            )
                            report.amended_questions_count += 1
                            report.amended_items.append(diff_item)
                        else:
                            report.unchanged_questions_count += 1
                    else:
                        report.unchanged_questions_count += 1

        return report
