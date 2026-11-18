"""
Media Synchronization & WebP Normalization Pipeline.
Integrates with ImageManager to safely fetch, validate with Pillow, convert to WebP,
and deduplicate via SHA-256 in master_database.sqlite.
"""
import os
import io
import base64
import requests
import sqlite3
from typing import Optional
from PIL import Image

from src.image_manager import ImageManager

class MediaSyncPipeline:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.img_mgr = ImageManager(conn)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }

    def process_raw_image(
        self,
        image_url: Optional[str] = None,
        image_base64: Optional[str] = None,
        ref_name: Optional[str] = None
    ) -> Optional[int]:
        """
        Processes image from either an external URL or base64 data string.
        Returns the image_id from master_database.sqlite or None if unavailable.
        """
        # 1. Base64 data provided
        if image_base64 and len(image_base64) > 50:
            try:
                b64_str = image_base64
                if "," in b64_str:
                    b64_str = b64_str.split(",", 1)[1]
                img_bytes = base64.b64decode(b64_str)
                return self.img_mgr.get_or_create_image_from_bytes(
                    img_bytes,
                    original_url=ref_name or "base64_data_bundle",
                    ext_hint="webp"
                )
            except Exception:
                pass

        # 2. URL provided
        if image_url and image_url.startswith("http"):
            # Check cache in ImageManager
            if image_url in self.img_mgr.url_cache:
                return self.img_mgr.url_cache[image_url]

            try:
                r = requests.get(image_url, headers=self.headers, timeout=12)
                if r.status_code == 200 and len(r.content) > 100:
                    ext = image_url.split(".")[-1].split("?")[0].lower()
                    if ext not in ["jpg", "jpeg", "png", "webp"]:
                        ext = "webp"
                    return self.img_mgr.get_or_create_image_from_bytes(
                        r.content,
                        original_url=image_url,
                        ext_hint=ext
                    )
            except Exception:
                pass

        return None
