import os
import sys

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from dotenv import load_dotenv
load_dotenv()

from src.bot.database import BotDatabase

db = BotDatabase()
history = db.get_user_exam_history(1956239701, limit=5)
print("Latest exam results for @a_aralovv (1956239701):")
for r in history:
    print(dict(r))
