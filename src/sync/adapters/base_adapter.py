"""
Base Source Adapter specification for external driving test portals.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class SourceStatus:
    source_code: str
    source_name: str
    source_url: str
    is_online: bool
    response_time_ms: float
    tickets_count: int
    estimated_questions_count: int
    last_checked: str
    error_message: Optional[str] = None
    extra_meta: Dict[str, Any] = field(default_factory=dict)

@dataclass
class RawQuestion:
    original_id: str
    ticket_num: int
    position: int
    language: str  # uz_latn, ru, uz_cyrl
    question_text: str
    options: List[str]
    correct_idx: int
    category_name: str = "Umumiy"
    category_slug: str = "umumiy"
    image_url: Optional[str] = None
    image_base64: Optional[str] = None
    explanation: Optional[str] = None
    raw_payload: Optional[str] = None

class BaseSourceAdapter(ABC):
    def __init__(self, source_code: str, source_name: str, base_url: str):
        self.source_code = source_code
        self.source_name = source_name
        self.base_url = base_url

    @abstractmethod
    def check_status(self) -> SourceStatus:
        """Ping the source, verify accessibility, and return current health status."""
        pass

    @abstractmethod
    def discover_tickets(self) -> List[int]:
        """Discover all available ticket numbers on the platform."""
        pass

    @abstractmethod
    def fetch_ticket(self, ticket_num: int, lang: str = "uz_latn") -> List[RawQuestion]:
        """Fetch all raw questions from a specific ticket in the requested language."""
        pass
