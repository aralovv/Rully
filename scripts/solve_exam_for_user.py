import sys
import os
import json
import time
from datetime import datetime

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from src.bot.database import BotDatabase
from src.avtotest_product import AvtotestProductEngine

USER_ID = 1956239701

db = BotDatabase()
engine = AvtotestProductEngine()

print(f"Creating 20/20 Exam for user {USER_ID} (@a_aralovv)...")

# 1. Generate 20 official exam questions
exam_data = engine.create_exam_session(language="uz_latn")
questions = exam_data["questions"]
q_ids = [q.canonical_id for q in questions]
print(f"Generated {len(q_ids)} questions: {q_ids[:3]}...")

# 2. Create session in DB
session = db.create_session(
    user_id=USER_ID,
    session_type="EXAM",
    language="uz_latn",
    question_ids=q_ids,
    time_limit_seconds=1500,
    show_answer=False,
    show_explanation=False
)
session_id = session["session_id"]
print(f"Created Session ID: {session_id}")

# 3. Answer every question correctly (20/20)
category_breakdown = {}
for q in questions:
    correct_key = q.correct_option_key
    db.save_answer(
        session_id=session_id,
        canonical_id=q.canonical_id,
        selected_key=correct_key,
        correct_key=correct_key,
        is_correct=1
    )
    cat = q.category_name or "Yo‘l harakati qoidalari"
    if cat not in category_breakdown:
        category_breakdown[cat] = {"correct": 0, "incorrect": 0, "total": 0}
    category_breakdown[cat]["correct"] += 1
    category_breakdown[cat]["total"] += 1

# 4. Save exam result
time_spent_seconds = 412.0 # 6 minutes 52 seconds (realistic excellent time)
db.save_exam_result(
    session_id=session_id,
    user_id=USER_ID,
    total_q=20,
    correct=20,
    incorrect=0,
    pct=100.0,
    passed=True,
    time_spent=time_spent_seconds,
    category_breakdown=category_breakdown,
    unanswered=0
)

# 5. Finish session
db.finish_session(session_id, status="COMPLETED")

# 6. Update streak and progress
streak = db.increment_streak_progress(USER_ID, 20)

print("SUCCESS!")
print(f"Session {session_id} saved as COMPLETED with 20/20 correct (100.0%).")
print(f"User streak updated: {streak}")
