import requests
import json
import sqlite3
import hashlib
import time
from bs4 import BeautifulSoup
from typing import Dict, List, Any, Optional
from src.image_manager import ImageManager

class YesPravaExtractor:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.img_mgr = ImageManager(conn)
        self.base_url = "https://yesprava.uz"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }
        self.build_id = self._get_build_id()
        self.source_id = self._get_source_id()

    def _get_build_id(self) -> str:
        try:
            r = requests.get(f"{self.base_url}/yhq-savollari/bilet-1", headers=self.headers, timeout=10)
            soup = BeautifulSoup(r.text, "html.parser")
            nd = soup.find("script", id="__NEXT_DATA__")
            if nd and nd.string:
                data = json.loads(nd.string)
                return data.get("buildId", "AbDtUWJB4hWGXB5JR47EV")
        except Exception as e:
            print(f"Warning: could not get buildId dynamically ({e}), using default fallback")
        return "AbDtUWJB4hWGXB5JR47EV"

    def _get_source_id(self) -> int:
        cur = self.conn.cursor()
        cur.execute("SELECT id FROM sources WHERE source_code = 'yesprava';")
        row = cur.fetchone()
        return row[0] if row else 1

    def fetch_ticket_json(self, ticket_num: int, lang: str = "uz_latn") -> Optional[Dict[str, Any]]:
        # Map languages to route prefix
        if lang == "uz_latn":
            route = f"yhq-savollari/bilet-{ticket_num}.json"
        elif lang == "ru":
            route = f"ru/bilety-pdd/bilet-{ticket_num}.json"
        elif lang == "uz_cyrl":
            route = f"kr/yhq-savollari/bilet-{ticket_num}.json"
        else:
            route = f"yhq-savollari/bilet-{ticket_num}.json"

        url = f"{self.base_url}/_next/data/{self.build_id}/{route}"
        try:
            r = requests.get(url, headers=self.headers, timeout=15)
            if r.status_code == 200:
                return r.json().get("pageProps", {}).get("data", {})
            else:
                print(f"Failed to fetch ticket {ticket_num} ({lang}): status {r.status_code}")
                return None
        except Exception as e:
            print(f"Error fetching ticket {ticket_num} ({lang}): {e}")
            return None

    def get_or_create_category(self, slug: str, name: str) -> int:
        cur = self.conn.cursor()
        cur.execute("SELECT id FROM categories WHERE slug = ?", (slug,))
        row = cur.fetchone()
        if row:
            return row[0]
        cur.execute("INSERT INTO categories (slug, name) VALUES (?, ?)", (slug, name))
        self.conn.commit()
        return cur.lastrowid

    def import_ticket(self, ticket_num: int, lang: str = "uz_latn", download_images: bool = True) -> int:
        data = self.fetch_ticket_json(ticket_num, lang=lang)
        if not data or "questions" not in data:
            print(f"No questions found in ticket {ticket_num}")
            return 0

        questions = data["questions"]
        imported = 0
        cur = self.conn.cursor()

        for q in questions:
            orig_id = str(q.get("id"))
            text = q.get("text", "").strip()
            options = q.get("options", [])
            correct_idx = q.get("correct")
            teaser = q.get("teaser")
            cat_name = q.get("category", "Umumiy")
            cat_slug = q.get("topic", "umumiy")
            image_url = q.get("image")

            if not text or not options:
                continue

            # Category
            cat_id = self.get_or_create_category(cat_slug, cat_name)

            # Image
            image_id = None
            if download_images and image_url:
                image_id = self.img_mgr.fetch_image_from_url(image_url)

            # Canonical hash (based on normalized text and sorted options to detect duplicates)
            norm_text = " ".join(text.lower().split())
            norm_opts = "|".join(" ".join(opt.lower().split()) for opt in options)
            hash_input = f"{lang}:{norm_text}:{norm_opts}".encode("utf-8")
            canonical_hash = hashlib.sha256(hash_input).hexdigest()

            # Question ID: UZ-YHQ-{hash[:10].upper()}
            qid = f"UZ-YHQ-{canonical_hash[:10].upper()}"

            # Insert question
            cur.execute("""
                INSERT INTO questions (id, canonical_hash, question_text, category_id, language, image_id, explanation, verification_status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'SOURCE_CONFIRMED', datetime('now'), datetime('now'))
                ON CONFLICT(canonical_hash) DO UPDATE SET
                    updated_at = datetime('now')
            """, (qid, canonical_hash, text, cat_id, lang, image_id, teaser))

            # Insert answers
            cur.execute("DELETE FROM answers WHERE question_id = ?", (qid,))
            for idx, opt_text in enumerate(options):
                opt_key = chr(ord('A') + idx)
                is_correct = 1 if idx == correct_idx else 0
                cur.execute("""
                    INSERT INTO answers (question_id, option_key, answer_text, is_correct, sort_order)
                    VALUES (?, ?, ?, ?, ?)
                """, (qid, opt_key, opt_text.strip(), is_correct, idx))

            # Insert question_sources
            raw_payload = json.dumps(q, ensure_ascii=False)
            cur.execute("""
                INSERT INTO question_sources (question_id, source_id, original_question_id, original_ticket, original_position, original_url, original_language, collection_timestamp, raw_payload)
                VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), ?)
            """, (qid, self.source_id, orig_id, ticket_num, q.get("position"), f"{self.base_url}/yhq-savollari/bilet-{ticket_num}", lang, raw_payload))

            imported += 1

        self.conn.commit()
        return imported
