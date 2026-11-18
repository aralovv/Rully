import os
import hashlib
import requests
import base64
import io
import sqlite3
from PIL import Image
from typing import Optional, Tuple, Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed

ORIGINAL_IMG_DIR = "data/images/original"
NORMALIZED_IMG_DIR = "data/images/normalized"

try:
    os.makedirs(ORIGINAL_IMG_DIR, exist_ok=True)
    os.makedirs(NORMALIZED_IMG_DIR, exist_ok=True)
except OSError:
    pass

class ImageManager:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.url_cache: Dict[str, int] = {}
        self._populate_cache()

    def _populate_cache(self):
        cur = self.conn.cursor()
        cur.execute("SELECT original_url, id FROM images WHERE original_url IS NOT NULL;")
        for row in cur.fetchall():
            self.url_cache[row[0]] = row[1]

    def get_or_create_image_from_bytes(self, image_bytes: bytes, original_url: Optional[str] = None, ext_hint: str = "webp") -> Optional[int]:
        if not image_bytes or len(image_bytes) < 100:
            return None

        sha256 = hashlib.sha256(image_bytes).hexdigest()

        # Check if already in database by SHA256
        cur = self.conn.cursor()
        cur.execute("SELECT id FROM images WHERE sha256 = ?", (sha256,))
        row = cur.fetchone()
        if row:
            img_id = row[0]
            if original_url:
                self.url_cache[original_url] = img_id
            return img_id

        # Verify image using PIL
        try:
            img = Image.open(io.BytesIO(image_bytes))
            width, height = img.size
            img_format = (img.format or ext_hint).lower()
        except Exception as e:
            return None

        filename = f"{sha256[:16]}.{img_format}"
        original_path = os.path.join(ORIGINAL_IMG_DIR, filename)

        # Save original bytes
        with open(original_path, "wb") as f:
            f.write(image_bytes)

        # Save normalized copy
        normalized_filename = f"{sha256[:16]}.webp"
        normalized_path = os.path.join(NORMALIZED_IMG_DIR, normalized_filename)
        try:
            img.save(normalized_path, format="WEBP", quality=95)
        except Exception:
            with open(normalized_path, "wb") as f:
                f.write(image_bytes)

        file_size = len(image_bytes)

        cur.execute("""
            INSERT INTO images (sha256, filename, original_url, local_path, width, height, format, file_size, license_status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PUBLIC_ACCESS', datetime('now'))
        """, (sha256, filename, original_url, original_path, width, height, img_format, file_size))
        self.conn.commit()
        img_id = cur.lastrowid
        if original_url:
            self.url_cache[original_url] = img_id
        return img_id

    def fetch_image_from_url(self, url: str) -> Optional[int]:
        if not url:
            return None

        if url in self.url_cache:
            return self.url_cache[url]

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }
        try:
            r = requests.get(url, headers=headers, timeout=12)
            if r.status_code == 200:
                ext_hint = "webp" if ".webp" in url else ("png" if ".png" in url else "jpg")
                return self.get_or_create_image_from_bytes(r.content, original_url=url, ext_hint=ext_hint)
            else:
                return None
        except Exception:
            return None

    def fetch_image_from_base64_data_url(self, data_url: str, ref_name: str = "") -> Optional[int]:
        if not data_url or not data_url.startswith("data:image"):
            return None

        cache_key = f"data_url:{ref_name}"
        if cache_key in self.url_cache:
            return self.url_cache[cache_key]

        try:
            header, encoded = data_url.split(",", 1)
            image_bytes = base64.b64decode(encoded)
            ext_hint = "webp" if "webp" in header else ("png" if "png" in header else "jpg")
            return self.get_or_create_image_from_bytes(image_bytes, original_url=cache_key, ext_hint=ext_hint)
        except Exception as e:
            return None

    def batch_preload_urls(self, urls: List[str], max_workers: int = 10):
        needed_urls = [u for u in set(urls) if u and u not in self.url_cache]
        if not needed_urls:
            return

        print(f"Preloading {len(needed_urls)} images with {max_workers} download threads...", flush=True)

        def download_worker(u):
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            for attempt in range(2):
                try:
                    r = requests.get(u, headers=headers, timeout=10)
                    if r.status_code == 200:
                        return u, r.content
                except Exception:
                    pass
            return u, None

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(download_worker, u) for u in needed_urls]
            done = 0
            for f in as_completed(futures):
                url, content = f.result()
                if content:
                    ext_hint = "webp" if ".webp" in url else ("png" if ".png" in url else "jpg")
                    self.get_or_create_image_from_bytes(content, original_url=url, ext_hint=ext_hint)
                done += 1
                if done % 50 == 0 or done == len(needed_urls):
                    print(f"  Preloaded {done}/{len(needed_urls)} images (active on disk)...", flush=True)
