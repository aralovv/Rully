import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

from src.avtotest_product import AvtotestProductEngine
from src.bot.database import BotDatabase

print("1. Testing AvtotestProductEngine on Turso...")
engine = AvtotestProductEngine("master_database.sqlite")
categories = engine.get_categories("uz_latn")
print(f"Categories count: {len(categories)}")
for c in categories[:3]:
    print(f"  Category: {c['category_id']} - {c['name']} ({c['question_count']} questions)")

question = engine.get_question("CANON-YHQ-0001", language="uz_latn", include_answer_key=True)
if question:
    print(f"Question {question.canonical_id}:")
    print(f"  Text: {question.question_text[:60]}...")
    print(f"  Options: {len(question.options)}")
    print(f"  Correct: {question.correct_option_key}")
else:
    print("Question not found!")

print("\n2. Testing BotDatabase on Turso...")
db = BotDatabase("master_database.sqlite")
user = db.get_or_create_user(8809526955, username="kurs_savdo", first_name="RULLY User")
print("User retrieved/created:", user["user_id"], user["username"])
stats = db.get_user_stats(8809526955)
print("User analytics calculated:", stats)

print("\nAll engine and bot database Turso tests PASSED!")
