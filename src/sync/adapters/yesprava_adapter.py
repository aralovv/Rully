"""
YesPrava (https://yesprava.uz) Source Adapter.
Extracts questions dynamically from Next.js pre-rendered JSON data routes.
"""
import time
import json
import requests
try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False
    BeautifulSoup = None
from typing import Dict, List, Optional, Any
from datetime import datetime

from src.sync.adapters.base_adapter import BaseSourceAdapter, SourceStatus, RawQuestion

class YesPravaAdapter(BaseSourceAdapter):
    DEFAULT_FALLBACK_BUILD_ID = "6kDFp5TL3SYFcM6FUrKz_"

    def __init__(self, base_url: str = "https://yesprava.uz", timeout: int = 15):
        super().__init__(
            source_code="yesprava",
            source_name="YesPrava",
            base_url=base_url
        )
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "uz,ru;q=0.9,en;q=0.8"
        }
        self.build_id: Optional[str] = None
        self._cached_tickets: List[int] = []
        self._last_ticket_discovery: float = 0.0

    def resolve_build_id(self, force_refresh: bool = False) -> str:
        if self.build_id and not force_refresh:
            return self.build_id

        try:
            r = requests.get(
                f"{self.base_url}/yhq-savollari/bilet-1",
                headers=self.headers,
                timeout=self.timeout
            )
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "html.parser")
                nd = soup.find("script", id="__NEXT_DATA__")
                if nd and nd.string:
                    data = json.loads(nd.string)
                    bid = data.get("buildId")
                    if bid:
                        self.build_id = bid
                        return self.build_id
        except Exception as e:
            pass

        self.build_id = self.build_id or self.DEFAULT_FALLBACK_BUILD_ID
        return self.build_id

    def check_status(self) -> SourceStatus:
        start_time = time.time()
        is_online = False
        error_msg = None
        tickets_count = 63
        bid = None

        try:
            bid = self.resolve_build_id(force_refresh=True)
            url = f"{self.base_url}/_next/data/{bid}/yhq-savollari/bilet-1.json"
            r = requests.get(url, headers=self.headers, timeout=self.timeout)
            duration = (time.time() - start_time) * 1000.0

            if r.status_code == 200:
                is_online = True
                tickets = self.discover_tickets(fast=True)
                tickets_count = len(tickets)
            else:
                error_msg = f"HTTP {r.status_code} on bilet-1"
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
            estimated_questions_count=tickets_count * 20,
            last_checked=datetime.now().isoformat(),
            error_message=error_msg,
            extra_meta={"build_id": bid}
        )

    def discover_tickets(self, fast: bool = False) -> List[int]:
        now = time.time()
        if self._cached_tickets and (now - self._last_ticket_discovery < 300) and not fast:
            return self._cached_tickets

        bid = self.resolve_build_id()
        # Baseline known tickets: 1 to 63
        discovered = list(range(1, 64))

        # Probe beyond 63
        probe_ticket = 64
        while probe_ticket <= 100:
            url = f"{self.base_url}/_next/data/{bid}/yhq-savollari/bilet-{probe_ticket}.json"
            try:
                r = requests.get(url, headers=self.headers, timeout=5)
                if r.status_code == 200:
                    data = r.json().get("pageProps", {}).get("data", {})
                    if data.get("questions"):
                        discovered.append(probe_ticket)
                        probe_ticket += 1
                        continue
                break
            except Exception:
                break

        self._cached_tickets = discovered
        self._last_ticket_discovery = now
        return discovered

    def _route_for_lang(self, ticket_num: int, lang: str) -> str:
        if lang == "ru":
            return f"ru/bilety-pdd/bilet-{ticket_num}.json"
        elif lang == "uz_cyrl":
            return f"kr/yhq-savollari/bilet-{ticket_num}.json"
        else:
            return f"yhq-savollari/bilet-{ticket_num}.json"

    def fetch_ticket(self, ticket_num: int, lang: str = "uz_latn") -> List[RawQuestion]:
        bid = self.resolve_build_id()
        route = self._route_for_lang(ticket_num, lang)
        url = f"{self.base_url}/_next/data/{bid}/{route}"

        try:
            r = requests.get(url, headers=self.headers, timeout=self.timeout)
            if r.status_code == 404:
                # If 404, maybe buildId changed, try refresh once
                bid = self.resolve_build_id(force_refresh=True)
                url = f"{self.base_url}/_next/data/{bid}/{route}"
                r = requests.get(url, headers=self.headers, timeout=self.timeout)

            if r.status_code != 200:
                return []

            data = r.json().get("pageProps", {}).get("data", {})
            raw_questions = data.get("questions", [])
            results: List[RawQuestion] = []

            for idx, q in enumerate(raw_questions, 1):
                text = str(q.get("text", "")).strip()
                options = [str(opt).strip() for opt in q.get("options", [])]
                if not text or not options:
                    continue

                correct_val = q.get("correct")
                try:
                    correct_idx = int(correct_val)
                except (ValueError, TypeError):
                    correct_idx = 0

                img_url = q.get("image")
                if img_url and img_url.startswith("/"):
                    img_url = f"{self.base_url}{img_url}"

                item = RawQuestion(
                    original_id=str(q.get("id", f"{ticket_num}_{idx}")),
                    ticket_num=ticket_num,
                    position=int(q.get("position") or idx),
                    language=lang,
                    question_text=text,
                    options=options,
                    correct_idx=correct_idx,
                    category_name=q.get("category") or "Umumiy",
                    category_slug=q.get("topic") or "umumiy",
                    image_url=img_url,
                    explanation=q.get("teaser"),
                    raw_payload=json.dumps(q, ensure_ascii=False)
                )
                results.append(item)

            return results
        except Exception as e:
            return []
