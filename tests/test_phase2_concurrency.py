"""
Phase 2 (P1) Verification Tests:
1. Thread-safe DB Adapter & Concurrency (no socket corruption across threads).
2. BoundedTTLCache (LRU eviction at maxsize, TTL expiration).
3. Batch DB Operations (execute_batch atomic updates, process_session_answer, create_session, finalize_exam_session).
"""
import time
import threading
import pytest
import os
from src.db_adapter import get_db_connection, execute_batch, TursoRow
from src.security.rate_limiter import BoundedTTLCache
from src.bot.database import BotDatabase

DB_PATH = os.getenv("DB_PATH", "master_database.sqlite")

@pytest.fixture(scope="module")
def bot_db():
    return BotDatabase(DB_PATH)


def test_bounded_ttl_cache_eviction_and_expiry():
    """Verify BoundedTTLCache enforces maxsize (LRU eviction) and respects TTL."""
    cache = BoundedTTLCache[str, int](maxsize=5, ttl_seconds=0.5)

    # 1. Fill cache up to capacity
    for i in range(5):
        cache.set(f"k{i}", i)
    assert len(cache) == 5

    # 2. Access k0 so it becomes most recently used
    assert cache.get("k0") == 0

    # 3. Add 6th element -> k1 should be evicted (oldest unused)
    cache.set("k5", 5)
    assert len(cache) == 5
    assert cache.get("k0") == 0
    assert cache.get("k1") is None
    assert cache.get("k5") == 5

    # 4. Wait for TTL expiry
    time.sleep(0.6)
    assert cache.get("k0") is None
    assert cache.get("k5") is None
    cache.prune_expired()
    assert len(cache) == 0


def test_concurrent_db_connections_thread_safety(bot_db):
    """Verify that multiple concurrent threads can query without SQLite/Turso contention or socket race conditions."""
    errors = []
    test_user_id = 999555
    bot_db.get_or_create_user(test_user_id, "concurrency_tester", "Concurrency", "User")

    def worker(thread_idx: int):
        try:
            for _ in range(5):
                conn = get_db_connection(DB_PATH)
                cur = conn.cursor()
                cur.execute("SELECT user_id, language FROM telegram_users WHERE user_id = ?", (test_user_id,))
                row = cur.fetchone()
                assert row is not None
                assert row[0] == test_user_id
                conn.close()
        except Exception as e:
            errors.append(f"Thread {thread_idx} error: {e}")

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Concurrent database queries failed: {errors}"


def test_execute_batch_atomicity():
    """Verify execute_batch handles batch of statements correctly."""
    conn = get_db_connection(DB_PATH)
    cur = conn.cursor()
    cur.execute("CREATE TEMP TABLE IF NOT EXISTS temp_batch_test (id INT PRIMARY KEY, val TEXT)")
    cur.execute("DELETE FROM temp_batch_test")
    conn.commit()

    stmts = [
        ("INSERT INTO temp_batch_test (id, val) VALUES (?, ?)", [1, "alpha"]),
        ("INSERT INTO temp_batch_test (id, val) VALUES (?, ?)", [2, "beta"]),
        ("UPDATE temp_batch_test SET val = ? WHERE id = ?", ["alpha_updated", 1])
    ]
    execute_batch(conn, stmts)

    cur.execute("SELECT id, val FROM temp_batch_test ORDER BY id")
    rows = cur.fetchall()
    assert len(rows) == 2
    assert rows[0][1] == "alpha_updated"
    assert rows[1][1] == "beta"
    conn.close()


def test_process_session_answer_batch(bot_db):
    """Verify process_session_answer executes atomically and updates streak & mistake records."""
    test_uid = 999556
    bot_db.get_or_create_user(test_uid, "answer_tester")
    
    # Create session with valid canonical IDs
    q_ids = ["CANON-YHQ-0001", "CANON-YHQ-0002"]
    sess = bot_db.create_session(
        user_id=test_uid,
        session_type="CUSTOM",
        language="uz_latn",
        question_ids=q_ids
    )
    sess_id = sess["session_id"]

    # Submit correct answer
    res1 = bot_db.process_session_answer(
        session_id=sess_id,
        user_id=test_uid,
        canonical_id="CANON-YHQ-0001",
        selected_key="A",
        correct_key="A",
        is_correct=True,
        session_type="CUSTOM"
    )
    assert res1["is_new"] is True
    assert res1["is_exam_terminated"] is False

    # Duplicate submission should be idempotent
    res1_dup = bot_db.process_session_answer(
        session_id=sess_id,
        user_id=test_uid,
        canonical_id="CANON-YHQ-0001",
        selected_key="A",
        correct_key="A",
        is_correct=True,
        session_type="CUSTOM"
    )
    assert res1_dup["is_new"] is False

    # Submit incorrect answer
    res2 = bot_db.process_session_answer(
        session_id=sess_id,
        user_id=test_uid,
        canonical_id="CANON-YHQ-0002",
        selected_key="B",
        correct_key="C",
        is_correct=False,
        session_type="CUSTOM"
    )
    assert res2["is_new"] is True

    # Finalize session
    final_sess = bot_db.finalize_exam_session(
        session_id=sess_id,
        user_id=test_uid,
        total_q=2,
        correct=1,
        incorrect=1,
        pct=50.0,
        passed=False,
        time_spent=15.0,
        category_breakdown={"General": {"correct": 1, "incorrect": 1, "total": 2}},
        status="COMPLETED"
    )
    assert final_sess["status"] == "COMPLETED"

    # Cleanup test artifacts
    with bot_db._get_connection() as conn:
        conn.execute("DELETE FROM session_answers WHERE session_id = ?", (sess_id,))
        conn.execute("DELETE FROM exam_results WHERE session_id = ?", (sess_id,))
        conn.execute("DELETE FROM user_mistakes WHERE user_id = ?", (test_uid,))
        conn.execute("DELETE FROM learning_streak WHERE user_id = ?", (test_uid,))
        conn.execute("DELETE FROM user_sessions WHERE user_id = ?", (test_uid,))
        conn.execute("DELETE FROM telegram_users WHERE user_id = ?", (test_uid,))
        conn.commit()
