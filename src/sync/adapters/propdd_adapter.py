"""
ProPDD (https://propdd.uz) Source Adapter.
Extracts questions and base64 chunked images from frontend static bundles.
"""
import time
import json
import hashlib
import requests
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from src.sync.adapters.base_adapter import BaseSourceAdapter, SourceStatus, RawQuestion

class ProPDDAdapter(BaseSourceAdapter):
    def __init__(self, base_url: str = "https://propdd.uz", timeout: int = 15):
        super().__init__(
            source_code="propdd",
            source_name="ProPDD",
            base_url=base_url
        )
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "*/*"
        }
        self.chunk_cache: Dict[str, Dict[str, str]] = {}
        self._cached_questions: Optional[List[Dict[str, Any]]] = None
        self._cached_hash: Optional[str] = None
        self._last_fetch_time: float = 0.0

    def _load_data_bundle(self, force_refresh: bool = False) -> Tuple[List[Dict[str, Any]], str]:
        now = time.time()
        if self._cached_questions is not None and not force_refresh and (now - self._last_fetch_time < 300):
            return self._cached_questions, self._cached_hash or ""

        url = f"{self.base_url}/data.js"
        r = requests.get(url, headers=self.headers, timeout=self.timeout)
        r.raise_for_status()

        content = r.text
        sha256 = hashlib.sha256(r.content).hexdigest()
        prefix = "window.UZ_QUESTIONS="

        if content.startswith(prefix):
            clean_json = content[len(prefix):].rstrip("; \n\r")
            data = json.loads(clean_json)
        else:
            data = []

        self._cached_questions = data
        self._cached_hash = sha256
        self._last_fetch_time = now
        return data, sha256

    def check_status(self) -> SourceStatus:
        start_time = time.time()
        is_online = False
        error_msg = None
        tickets_count = 0
        sha256 = None

        try:
            data, sha256 = self._load_data_bundle(force_refresh=True)
            duration = (time.time() - start_time) * 1000.0
            is_online = len(data) > 0
            tickets = set(q.get("t") for q in data if q.get("t") is not None)
            tickets_count = len(tickets)
        except Exception as e:
            duration = (time.time() - start_time) * 1000.0
            error_msg = str(e)

        return SourceStatus(
            source_code=self.source_code,
            source_name=self.source_name,
            source_url=self.base_url,
            is_online=is_online,
            response_time_ms=round(duration, 1),
            tickets_count=tickets_count,
            estimated_questions_count=len(self._cached_questions or []),
            last_checked=datetime.now().isoformat(),
            error_message=error_msg,
            extra_meta={"data_js_sha256": sha256}
        )

    def discover_tickets(self) -> List[int]:
        try:
            data, _ = self._load_data_bundle()
            tickets = sorted(list(set(int(q.get("t")) for q in data if q.get("t") is not None)))
            return tickets
        except Exception:
            return list(range(1, 62))

    def get_image_base64(self, chunk_file: str, img_name: str) -> Optional[str]:
        if not chunk_file or not img_name:
            return None

        if chunk_file not in self.chunk_cache:
            chunk_url = f"{self.base_url}/img/{chunk_file}"
            try:
                r = requests.get(chunk_url, headers=self.headers, timeout=10)
                if r.status_code == 200:
                    self.chunk_cache[chunk_file] = r.json()
                else:
                    self.chunk_cache[chunk_file] = {}
            except Exception:
                self.chunk_cache[chunk_file] = {}

        return self.chunk_cache[chunk_file].get(img_name)

    def fetch_ticket(self, ticket_num: int, lang: str = "uz_latn", download_images: bool = True) -> List[RawQuestion]:
        lang_key = "lat" if lang == "uz_latn" else ("cyr" if lang == "uz_cyrl" else "ru")
        data, _ = self._load_data_bundle()

        ticket_questions = [q for q in data if q.get("t") == ticket_num]
        results: List[RawQuestion] = []

        for idx, q in enumerate(ticket_questions, 1):
            lang_data = q.get(lang_key)
            if not lang_data or len(lang_data) < 3:
                continue

            text = str(lang_data[0]).strip()
            options = [str(opt).strip() for opt in lang_data[1]]
            if not text or not options:
                continue

            try:
                correct_idx = int(lang_data[2])
            except (ValueError, TypeError):
                correct_idx = 0

            img_name = q.get("img")
            chunk_file = q.get("ib")
            img_b64 = None
            if download_images and img_name and chunk_file:
                img_b64 = self.get_image_base64(chunk_file, img_name)

            item = RawQuestion(
                original_id=str(q.get("id", f"{ticket_num}_{idx}")),
                ticket_num=ticket_num,
                position=idx,
                language=lang,
                question_text=text,
                options=options,
                correct_idx=correct_idx,
                category_name="Umumiy",
                category_slug="umumiy",
                image_url=None,
                image_base64=img_b64,
                raw_payload=json.dumps(q, ensure_ascii=False)
            )
            results.append(item)

        return results
