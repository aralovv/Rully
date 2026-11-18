import requests
import json
import sqlite3
import hashlib
import os
from typing import Dict, List, Any, Optional
from src.image_manager import ImageManager

class ProPDDExtractor:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.img_mgr = ImageManager(conn)
        self.base_url = "https://propdd.uz"
        self.source_id = self._get_source_id()
        self.questions_data = self._load_questions_data()
        self.chunk_cache = {}

    def _get_source_id(self) -> int:
        cur = self.conn.cursor()
        cur.execute("SELECT id FROM sources WHERE source_code = 'propdd';")
        row = cur.fetchone()
        return row[0] if row else 2

    def _load_questions_data(self) -> List[Dict[str, Any]]:
        local_path = "data/sources/propdd_data.js"
        if os.path.exists(local_path):
            with open(local_path, "r", encoding="utf-8") as f:
                content = f.read()
        else:
            headers = {"User-Agent": "Mozilla/5.0"}
            r = requests.get(f"{self.base_url}/data.js", headers=headers, timeout=30)
            content = r.text
            with open(local_path, "w", encoding="utf-8") as f:
                f.write(content)

        prefix = "window.UZ_QUESTIONS="
        if content.startswith(prefix):
            js_data = content[len(prefix):].rstrip("; \n")
            return json.loads(js_data)
        return []

    def get_image_data_url(self, chunk_file: str, img_name: str) -> Optional[str]:
        if not chunk_file or not img_name:
            return None

        if chunk_file not in self.chunk_cache:
            chunk_url = f"{self.base_url}/img/{chunk_file}"
            headers = {"User-Agent": "Mozilla/5.0"}
            try:
                r = requests.get(chunk_url, headers=headers, timeout=10)
                if r.status_code == 200:
                    self.chunk_cache[chunk_file] = r.json()
                else:
                    self.chunk_cache[chunk_file] = {}
            except Exception as e:
                print(f"Error fetching image chunk {chunk_file}: {e}")
                self.chunk_cache[chunk_file] = {}

        return self.chunk_cache[chunk_file].get(img_name)

    def import_ticket(self, ticket_num: int, lang: str = "uz_latn", download_images: bool = True) -> int:
        # Lang mapping
        lang_key = "lat" if lang == "uz_latn" else ("cyr" if lang == "uz_cyrl" else "ru")
        
        ticket_questions = [q for q in self.questions_data if q.get("t") == ticket_num]
        if not ticket_questions:
            print(f"No questions found for ticket {ticket_num} in propdd")
            return 0

        cur = self.conn.cursor()
        imported = 0

        for pos, q in enumerate(ticket_questions, 1):
            orig_id = str(q.get("id"))
            lang_data = q.get(lang_key)
            if not lang_data or len(lang_data) < 3:
                continue

            text = lang_data[0].strip()
            options = lang_data[1]
            correct_idx = lang_data[2]
            img_name = q.get("img")
            chunk_file = q.get("ib")

            if not text or not options:
                continue

            # Image resolution
            image_id = None
            if download_images and img_name and chunk_file:
                data_url = self.get_image_data_url(chunk_file, img_name)
                if data_url:
                    image_id = self.img_mgr.fetch_image_from_base64_data_url(data_url, ref_name=img_name)

            # Canonical hash
            norm_text = " ".join(text.lower().split())
            norm_opts = "|".join(" ".join(opt.lower().split()) for opt in options)
            hash_input = f"{lang}:{norm_text}:{norm_opts}".encode("utf-8")
            canonical_hash = hashlib.sha256(hash_input).hexdigest()

            qid = f"UZ-YHQ-{canonical_hash[:10].upper()}"

            # Insert question
            cur.execute("""
                INSERT INTO questions (id, canonical_hash, question_text, category_id, language, image_id, explanation, verification_status, created_at, updated_at)
                VALUES (?, ?, ?, NULL, ?, ?, NULL, 'SOURCE_CONFIRMED', datetime('now'), datetime('now'))
                ON CONFLICT(canonical_hash) DO UPDATE SET
                    updated_at = datetime('now')
            """, (qid, canonical_hash, text, lang, image_id))

            # Insert answers
            cur.execute("DELETE FROM answers WHERE question_id = ?", (qid,))
            for idx, opt_text in enumerate(options):
                opt_key = chr(ord('A') + idx)
                is_correct = 1 if idx == correct_idx else 0
                cur.execute("""
                    INSERT INTO answers (question_id, option_key, answer_text, is_correct, sort_order)
                    VALUES (?, ?, ?, ?, ?)
                """, (qid, opt_key, str(opt_text).strip(), is_correct, idx))

            # Insert question_sources
            raw_payload = json.dumps(q, ensure_ascii=False)
            cur.execute("""
                INSERT INTO question_sources (question_id, source_id, original_question_id, original_ticket, original_position, original_url, original_language, collection_timestamp, raw_payload)
                VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), ?)
            """, (qid, self.source_id, orig_id, ticket_num, pos, f"{self.base_url}/trainer", lang, raw_payload))

            imported += 1

        self.conn.commit()
        return imported
