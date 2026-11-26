"""
Database Migration and Schema Extension for Admin Control Panel & MTProto Payment System.
Safely adds required entities, indexes, and seed records without modifying or deleting existing data.
"""

import sqlite3
import logging
from datetime import datetime
from src.db_adapter import is_turso_enabled, get_db_connection

logger = logging.getLogger(__name__)

MIGRATION_SQL = """
-- 1. Admin Users
CREATE TABLE IF NOT EXISTS admin_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    telegram_id INTEGER NOT NULL DEFAULT 1956239701,
    role TEXT NOT NULL DEFAULT 'SUPERADMIN',
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    last_login_at TEXT
);

-- 2. Admin Sessions
CREATE TABLE IF NOT EXISTS admin_sessions (
    session_id TEXT PRIMARY KEY,
    admin_id INTEGER NOT NULL,
    ip_address TEXT,
    user_agent TEXT,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    is_revoked INTEGER NOT NULL DEFAULT 0,
    last_activity_at TEXT NOT NULL,
    FOREIGN KEY (admin_id) REFERENCES admin_users(id) ON DELETE CASCADE
);

-- 3. Admin OTP Challenges
CREATE TABLE IF NOT EXISTS admin_otp_challenges (
    challenge_id TEXT PRIMARY KEY,
    admin_id INTEGER NOT NULL,
    otp_hash TEXT NOT NULL,
    telegram_id INTEGER NOT NULL,
    attempts_count INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 5,
    is_used INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    FOREIGN KEY (admin_id) REFERENCES admin_users(id) ON DELETE CASCADE
);

-- 4. Subscription Plans (dynamic database-backed)
CREATE TABLE IF NOT EXISTS subscription_plans (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    duration_days INTEGER NOT NULL,
    base_price_uzs INTEGER NOT NULL,
    description TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    display_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- 5. Subscription Price History
CREATE TABLE IF NOT EXISTS subscription_price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id TEXT NOT NULL,
    old_price_uzs INTEGER NOT NULL,
    new_price_uzs INTEGER NOT NULL,
    changed_by_admin TEXT NOT NULL,
    reason TEXT,
    changed_at TEXT NOT NULL,
    FOREIGN KEY (plan_id) REFERENCES subscription_plans(id)
);

-- 6. Payment Cards
CREATE TABLE IF NOT EXISTS payment_cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cardholder_name TEXT NOT NULL,
    card_number_encrypted TEXT NOT NULL,
    card_number_masked TEXT NOT NULL,
    card_suffix TEXT NOT NULL,
    card_type TEXT NOT NULL DEFAULT 'HUMO',
    display_name TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    is_monitoring INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- 7. Payment Orders
CREATE TABLE IF NOT EXISTS payment_orders (
    order_id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    plan_id TEXT NOT NULL,
    plan_name TEXT NOT NULL,
    duration_days INTEGER NOT NULL,
    base_price_uzs INTEGER NOT NULL,
    suffix_uzs INTEGER NOT NULL,
    final_amount_uzs INTEGER NOT NULL,
    card_id INTEGER NOT NULL,
    card_suffix TEXT NOT NULL,
    card_number_masked TEXT NOT NULL,
    cardholder_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    paid_at TEXT,
    FOREIGN KEY (user_id) REFERENCES telegram_users(user_id),
    FOREIGN KEY (card_id) REFERENCES payment_cards(id),
    FOREIGN KEY (plan_id) REFERENCES subscription_plans(id)
);

-- Unique index enforcing at most one active (PENDING) order per user
CREATE UNIQUE INDEX IF NOT EXISTS idx_active_order_user ON payment_orders(user_id) WHERE status = 'PENDING';

-- Unique index preventing duplicate active payment amounts on the same card
CREATE UNIQUE INDEX IF NOT EXISTS idx_active_order_amount_card ON payment_orders(card_id, final_amount_uzs) WHERE status = 'PENDING';

-- Indexes for fast order querying and expiration checking
CREATE INDEX IF NOT EXISTS idx_payment_orders_status ON payment_orders(status);
CREATE INDEX IF NOT EXISTS idx_payment_orders_expires_at ON payment_orders(expires_at);
CREATE INDEX IF NOT EXISTS idx_payment_orders_user_id ON payment_orders(user_id);

-- 8. Payment Events (Raw normalized MTProto Humocardbot events)
CREATE TABLE IF NOT EXISTS payment_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_fingerprint TEXT UNIQUE NOT NULL,
    source_chat TEXT NOT NULL,
    message_id INTEGER NOT NULL,
    transaction_type TEXT NOT NULL,
    incoming_amount_uzs INTEGER NOT NULL,
    resulting_balance_uzs INTEGER,
    card_suffix TEXT NOT NULL,
    payment_source TEXT,
    transaction_timestamp TEXT NOT NULL,
    raw_message TEXT NOT NULL,
    status TEXT NOT NULL,
    matched_order_id TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_payment_events_fingerprint ON payment_events(event_fingerprint);
CREATE INDEX IF NOT EXISTS idx_payment_events_status ON payment_events(status);

-- 9. Payment Transactions (Financial ledger of verified payments)
CREATE TABLE IF NOT EXISTS payment_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT UNIQUE NOT NULL,
    user_id INTEGER NOT NULL,
    event_id INTEGER,
    amount_uzs INTEGER NOT NULL,
    plan_id TEXT NOT NULL,
    card_suffix TEXT NOT NULL,
    payment_timestamp TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (order_id) REFERENCES payment_orders(order_id),
    FOREIGN KEY (user_id) REFERENCES telegram_users(user_id),
    FOREIGN KEY (event_id) REFERENCES payment_events(id)
);

CREATE INDEX IF NOT EXISTS idx_payment_transactions_user ON payment_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_payment_transactions_created ON payment_transactions(created_at);

-- 10. Unmatched Payments
CREATE TABLE IF NOT EXISTS unmatched_payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL,
    amount_uzs INTEGER NOT NULL,
    card_suffix TEXT NOT NULL,
    payment_source TEXT,
    transaction_timestamp TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'UNRESOLVED',
    resolution_notes TEXT,
    resolved_by_admin TEXT,
    resolved_at TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (event_id) REFERENCES payment_events(id)
);

-- 11. Payment Review Cases (Late or disputed payments)
CREATE TABLE IF NOT EXISTS payment_review_cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT NOT NULL,
    event_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    amount_uzs INTEGER NOT NULL,
    reason TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    admin_notes TEXT,
    resolved_by_admin TEXT,
    resolved_at TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (order_id) REFERENCES payment_orders(order_id),
    FOREIGN KEY (event_id) REFERENCES payment_events(id),
    FOREIGN KEY (user_id) REFERENCES telegram_users(user_id)
);

-- 11b. Telegram Stars (XTR) Orders (native in-app digital goods checkout)
CREATE TABLE IF NOT EXISTS payment_stars_orders (
    order_id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    plan_id TEXT NOT NULL,
    plan_name TEXT NOT NULL,
    duration_days INTEGER NOT NULL,
    stars_amount INTEGER NOT NULL,
    uzs_equivalent INTEGER NOT NULL,
    payload TEXT UNIQUE NOT NULL,
    invoice_url TEXT,
    telegram_payment_charge_id TEXT UNIQUE,
    provider_payment_charge_id TEXT,
    status TEXT NOT NULL DEFAULT 'PENDING',
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    paid_at TEXT,
    FOREIGN KEY (user_id) REFERENCES telegram_users(user_id),
    FOREIGN KEY (plan_id) REFERENCES subscription_plans(id)
);

CREATE INDEX IF NOT EXISTS idx_stars_orders_user ON payment_stars_orders(user_id);
CREATE INDEX IF NOT EXISTS idx_stars_orders_status ON payment_stars_orders(status);
CREATE INDEX IF NOT EXISTS idx_stars_orders_payload ON payment_stars_orders(payload);

-- 12. User Activity Events (Real activity telemetry)
CREATE TABLE IF NOT EXISTS user_activity_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    event_name TEXT NOT NULL,
    event_data TEXT,
    ip_address TEXT,
    user_agent TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES telegram_users(user_id)
);

CREATE INDEX IF NOT EXISTS idx_user_activity_user_id ON user_activity_events(user_id);
CREATE INDEX IF NOT EXISTS idx_user_activity_event_name ON user_activity_events(event_name);
CREATE INDEX IF NOT EXISTS idx_user_activity_created_at ON user_activity_events(created_at);

-- 13. MTProto Accounts
CREATE TABLE IF NOT EXISTS mtproto_accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone_number TEXT NOT NULL,
    session_encrypted TEXT NOT NULL,
    tg_user_id INTEGER,
    tg_username TEXT,
    tg_first_name TEXT,
    monitored_bot TEXT NOT NULL DEFAULT 'Humocardbot',
    connection_status TEXT NOT NULL DEFAULT 'DISCONNECTED',
    last_event_at TEXT,
    last_payment_at TEXT,
    last_error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- 14. System Settings
CREATE TABLE IF NOT EXISTS system_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    description TEXT,
    updated_at TEXT NOT NULL
);

-- 15. AI Assistant Conversations & Usage Limits
CREATE TABLE IF NOT EXISTS ai_conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    session_id TEXT NOT NULL DEFAULT 'default',
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    meta_json TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_ai_conv_user ON ai_conversations(user_id, session_id);

CREATE TABLE IF NOT EXISTS ai_usage_limits (
    user_id INTEGER NOT NULL,
    usage_date TEXT NOT NULL,
    request_count INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (user_id, usage_date)
);

-- 15. Staged Questions (Human-in-the-Loop Review Queue)
CREATE TABLE IF NOT EXISTS staged_questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_code TEXT NOT NULL,
    source_ticket INTEGER,
    source_position INTEGER,
    change_type TEXT NOT NULL DEFAULT 'NEW_QUESTION',
    existing_canonical_id TEXT,
    category_slug TEXT DEFAULT 'umumiy',
    category_name TEXT DEFAULT 'Umumiy',
    image_url TEXT,
    staged_image_id INTEGER,
    text_uz_latn TEXT NOT NULL,
    text_uz_cyrl TEXT,
    text_ru TEXT,
    options_json TEXT NOT NULL,
    correct_option_key TEXT NOT NULL,
    explanation TEXT,
    raw_payload TEXT,
    review_status TEXT NOT NULL DEFAULT 'PENDING_REVIEW',
    reviewer_notes TEXT,
    reviewed_by TEXT,
    reviewed_at TEXT,
    published_canonical_id TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (staged_image_id) REFERENCES images(id)
);

CREATE INDEX IF NOT EXISTS idx_staged_status ON staged_questions(review_status);
CREATE INDEX IF NOT EXISTS idx_staged_slot ON staged_questions(source_code, source_ticket, source_position);

-- 16. RULLY 2.0 User Ticket (Bilet 01..67) Progress Tracking
CREATE TABLE IF NOT EXISTS user_ticket_progress (
    user_id INTEGER NOT NULL,
    ticket_number INTEGER NOT NULL,
    total_questions INTEGER NOT NULL DEFAULT 20,
    best_correct INTEGER NOT NULL DEFAULT 0,
    best_percentage REAL NOT NULL DEFAULT 0.0,
    attempts_count INTEGER NOT NULL DEFAULT 1,
    is_passed INTEGER NOT NULL DEFAULT 0,
    last_session_id TEXT,
    last_attempted_at TEXT NOT NULL,
    PRIMARY KEY (user_id, ticket_number),
    FOREIGN KEY (user_id) REFERENCES telegram_users(user_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_ticket_progress_user ON user_ticket_progress(user_id);
CREATE INDEX IF NOT EXISTS idx_session_answers_user_canon ON session_answers(user_id, canonical_id, is_correct);

-- 17. RULLY 2.0 Phase 5 SM-2 Spaced Repetition Memory State
CREATE TABLE IF NOT EXISTS user_question_srs (
    user_id INTEGER NOT NULL,
    canonical_id TEXT NOT NULL,
    ease_factor REAL NOT NULL DEFAULT 2.5,
    interval_days INTEGER NOT NULL DEFAULT 0,
    repetitions INTEGER NOT NULL DEFAULT 0,
    lapses INTEGER NOT NULL DEFAULT 0,
    last_quality INTEGER NOT NULL DEFAULT 0,
    last_reviewed_at TEXT NOT NULL,
    next_review_at TEXT NOT NULL,
    PRIMARY KEY (user_id, canonical_id),
    FOREIGN KEY (user_id) REFERENCES telegram_users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (canonical_id) REFERENCES canonical_questions(canonical_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_srs_user_due ON user_question_srs(user_id, next_review_at);
CREATE INDEX IF NOT EXISTS idx_srs_user_reps ON user_question_srs(user_id, repetitions, lapses);
"""

def run_migrations(db_path: str = "master_database.sqlite"):
    """Applies all schema migrations and seeds initial required records."""
    if is_turso_enabled():
        logger.info("Turso cloud database is enabled; skipping local SQLite file migrations.")
        return

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    
    with conn:
        conn.executescript(MIGRATION_SQL)
        
        # Check and add columns to telegram_users if not present
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(telegram_users);")
        columns = [row[1] for row in cursor.fetchall()]
        
        if "block_reason" not in columns:
            cursor.execute("ALTER TABLE telegram_users ADD COLUMN block_reason TEXT DEFAULT NULL;")
        if "blocked_at" not in columns:
            cursor.execute("ALTER TABLE telegram_users ADD COLUMN blocked_at TEXT DEFAULT NULL;")
        if "blocked_by" not in columns:
            cursor.execute("ALTER TABLE telegram_users ADD COLUMN blocked_by TEXT DEFAULT NULL;")
            
        # Seed default subscription plans if empty
        cursor.execute("SELECT COUNT(*) FROM subscription_plans;")
        if cursor.fetchone()[0] == 0:
            now_str = datetime.utcnow().isoformat()
            cursor.execute("""
                INSERT INTO subscription_plans (id, name, duration_days, base_price_uzs, description, is_active, display_order, created_at, updated_at)
                VALUES 
                ('pro_14', '14 kunlik PRO (2 hafta)', 14, 14000, '2 hafta davomida davlat imtihoni, xatolar banki va shpargalkadan to‘liq foydalanish', 1, 1, ?, ?),
                ('pro_30', '30 kunlik PRO (1 oy)', 30, 25000, '1 oy davomida barcha imtiyozli funksiyalar va chuqur tahlillarga cheksiz kirish', 1, 2, ?, ?);
            """, (now_str, now_str, now_str, now_str))

        # Seed default payment card if empty
        cursor.execute("SELECT COUNT(*) FROM payment_cards;")
        if cursor.fetchone()[0] == 0:
            now_str = datetime.utcnow().isoformat()
            # Demo default card (Humocard *5370, Anvarjon Aralov)
            cursor.execute("""
                INSERT INTO payment_cards (cardholder_name, card_number_encrypted, card_number_masked, card_suffix, card_type, display_name, is_active, is_monitoring, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 1, 1, ?, ?);
            """, (
                "ANVARJON ARALOV",
                "ENC:9860123456785370",
                "9860 **** **** 5370",
                "5370",
                "HUMO",
                "Asosiy HUMO kartasi (*5370)",
                now_str,
                now_str
            ))

        # Seed initial system settings
        default_settings = [
            ("mtproto_monitored_bot", "Humocardbot", "Target Telegram bot username for payment notifications"),
            ("payment_order_expiry_minutes", "15", "Lifetime of a payment order before automatic expiration"),
            ("order_suffix_min", "1", "Minimum random suffix added to base price in UZS"),
            ("order_suffix_max", "999", "Maximum random suffix added to base price in UZS"),
            ("otp_expiry_seconds", "300", "Admin Telegram OTP expiration time (5 minutes)"),
            ("otp_max_attempts", "5", "Maximum incorrect OTP attempts before invalidation"),
            ("admin_telegram_id", "1956239701", "Administrator Telegram user ID for OTP delivery")
        ]
        now_str = datetime.utcnow().isoformat()
        for k, v, d in default_settings:
            cursor.execute("""
                INSERT OR IGNORE INTO system_settings (key, value, description, updated_at)
                VALUES (?, ?, ?, ?);
            """, (k, v, d, now_str))

        conn.commit()
        from src.db.migrations_v2 import apply_all_migrations
        apply_all_migrations(conn)

    conn.close()
    logger.info("Database migration completed successfully!")


def run_turso_migrations(apply: bool = False):
    """
    Explicit Turso schema migration runner (Phase 1D/1E & Phase 5).
    Never runs implicitly on import or FastAPI startup unless explicitly invoked.
    """
    if not is_turso_enabled():
        raise RuntimeError("Turso is not enabled in environment configuration.")
    if not apply:
        conn = get_db_connection()
        try:
            from src.db.migrations_v2 import verify_phase5_schema_parity, verify_schema_parity
            p1 = verify_schema_parity(conn)
            p5 = verify_phase5_schema_parity(conn)
            return {
                "dry_run": True,
                "parity": {"passed": bool(p1["passed"] and p5["passed"]), "phase1": p1, "phase5": p5},
            }
        finally:
            conn.close()
    conn = get_db_connection()
    try:
        from src.db.migrations_v2 import apply_all_migrations
        return apply_all_migrations(conn)
    finally:
        conn.close()

if __name__ == "__main__":
    run_migrations()
    print("Migration executed successfully!")
