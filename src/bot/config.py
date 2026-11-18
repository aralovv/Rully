"""
Configuration settings for Avtotest Telegram Bot.
"""
import os
from typing import List
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "8657532177:AAGsyMFpzuwPus9jOdFRNP8f65qa8E-4q8g")
DB_PATH: str = os.getenv("DB_PATH", "master_database.sqlite")

# Admin IDs (comma-separated integers in environment variable, or default list)
_admin_ids_raw = os.getenv("ADMIN_IDS", "")
ADMIN_IDS: List[int] = [
    int(x.strip()) for x in _admin_ids_raw.split(",") if x.strip().isdigit()
]

# Official exam simulation configuration
EXAM_TOTAL_QUESTIONS: int = int(os.getenv("EXAM_TOTAL_QUESTIONS", "20"))
EXAM_TIME_LIMIT_SECONDS: int = int(os.getenv("EXAM_TIME_LIMIT_SECONDS", str(25 * 60)))  # 25 minutes
EXAM_PASSING_SCORE: int = int(os.getenv("EXAM_PASSING_SCORE", "18"))  # 18 out of 20 to pass

# Quick test defaults
QUICK_TEST_QUESTIONS: int = int(os.getenv("QUICK_TEST_QUESTIONS", "10"))

# Bot info
BOT_NAME: str = "RULLY"
BOT_VERSION: str = "2.0.0-production"

# Telegram Mini App URL (HTTPS required by Telegram Bot API)
WEB_APP_URL: str = os.getenv("WEB_APP_URL", "https://subcommittee-teaching-continuity-mask.trycloudflare.com?v=3.3.0")
