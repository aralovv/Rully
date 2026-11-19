"""
Payment Order Management Service.
Handles:
- Atomic order creation and idempotent reopening of existing orders
- Unique payment suffix allocation (1..999 UZS)
- Active monitoring card assignment
- Enforcing exactly one active order per user
- Server-side 15-minute order expiration
"""

import os
import sqlite3
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from src.security.crypto import decrypt_data

DB_PATH = os.getenv("DB_PATH", "master_database.sqlite")
ORDER_LIFETIME_MINUTES = 15


from src.db_adapter import get_db_connection

def _get_connection():
    return get_db_connection(DB_PATH)


def get_active_monitoring_card() -> Optional[Dict[str, Any]]:
    """Retrieves the active designated payment card for receiving transfers."""
    with _get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT * FROM payment_cards 
            WHERE is_active = 1 AND is_monitoring = 1 
            ORDER BY id ASC LIMIT 1
        """)
        row = c.fetchone()
        return dict(row) if row else None


def get_order_by_id(order_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves full order details by order_id, enforcing real-time expiration check."""
    with _get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM payment_orders WHERE order_id = ?", (order_id,))
        row = c.fetchone()
        if not row:
            return None
        res = dict(row)

        # Real-time expiration enforcement for pending orders
        now_dt = datetime.utcnow()
        if res.get("expires_at"):
            try:
                expires_dt = datetime.fromisoformat(res["expires_at"].replace("Z", ""))
                if res.get("status") == "PENDING" and now_dt >= expires_dt:
                    c.execute("UPDATE payment_orders SET status = 'EXPIRED' WHERE order_id = ?", (order_id,))
                    conn.commit()
                    res["status"] = "EXPIRED"
                diff = expires_dt - now_dt
                res["remaining_seconds"] = max(0, int(diff.total_seconds()))
            except Exception:
                res["remaining_seconds"] = 0
        else:
            res["remaining_seconds"] = 0

        c.execute("SELECT card_number_encrypted FROM payment_cards WHERE id = ?", (row["card_id"],))
        c_row = c.fetchone()
        if c_row and c_row["card_number_encrypted"]:
            try:
                raw = decrypt_data(c_row["card_number_encrypted"]).replace(" ", "")
                res["card_number_raw"] = raw
                if len(raw) == 16:
                    res["card_number_formatted"] = " ".join([raw[i:i+4] for i in range(0, 16, 4)])
                else:
                    res["card_number_formatted"] = raw
            except Exception:
                res["card_number_raw"] = res.get("card_number_masked", "")
                res["card_number_formatted"] = res.get("card_number_masked", "")
        return res


def get_user_active_order(user_id: int) -> Optional[Dict[str, Any]]:
    """
    Retrieves the currently unexpired PENDING order for a user, if any.
    If an existing pending order has passed its expiration time, marks it EXPIRED.
    """
    now_dt = datetime.utcnow()
    now_str = now_dt.isoformat()

    with _get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT * FROM payment_orders 
            WHERE user_id = ? AND status = 'PENDING'
            ORDER BY created_at DESC LIMIT 1
        """, (user_id,))
        row = c.fetchone()

        if not row:
            return None

        # Check expiration
        expires_dt = datetime.fromisoformat(row["expires_at"].replace("Z", ""))
        if now_dt >= expires_dt:
            c.execute("UPDATE payment_orders SET status = 'EXPIRED' WHERE order_id = ?", (row["order_id"],))
            conn.commit()
            return None

        order_dict = dict(row)
        # Calculate remaining seconds
        diff = expires_dt - now_dt
        order_dict["remaining_seconds"] = max(0, int(diff.total_seconds()))

        # Attach raw & formatted card number
        c.execute("SELECT card_number_encrypted FROM payment_cards WHERE id = ?", (row["card_id"],))
        c_row = c.fetchone()
        if c_row and c_row["card_number_encrypted"]:
            try:
                raw = decrypt_data(c_row["card_number_encrypted"]).replace(" ", "")
                order_dict["card_number_raw"] = raw
                if len(raw) == 16:
                    order_dict["card_number_formatted"] = " ".join([raw[i:i+4] for i in range(0, 16, 4)])
                else:
                    order_dict["card_number_formatted"] = raw
            except Exception:
                order_dict["card_number_raw"] = order_dict.get("card_number_masked", "")
                order_dict["card_number_formatted"] = order_dict.get("card_number_masked", "")
        return order_dict


def expire_stale_orders() -> int:
    """Scans all PENDING orders past their expiration timestamp and marks them EXPIRED."""
    now_str = datetime.utcnow().isoformat()
    with _get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            UPDATE payment_orders 
            SET status = 'EXPIRED' 
            WHERE status = 'PENDING' AND expires_at <= ?
        """, (now_str,))
        count = c.rowcount
        conn.commit()
        return count


def get_active_orders_count() -> int:
    """Returns the current number of active PENDING unexpired orders."""
    now_str = datetime.utcnow().isoformat()
    with _get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT COUNT(*) FROM payment_orders 
            WHERE status = 'PENDING' AND expires_at > ?
        """, (now_str,))
        return c.fetchone()[0]


def create_or_get_payment_order(user_id: int, plan_id: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Creates a new payment order or reopens an existing unexpired order for the user.
    Enforces:
    1. If user already has an active order for the SAME plan -> return existing order.
    2. If user has an active order for a DIFFERENT plan -> expire old order, create new order.
    3. Exactly one active order per user.
    4. Unique payment suffix (1..999 UZS) ensuring final_amount is unique on the card.
    5. Immutable order snapshot.
    """
    # 1. First expire any stale orders in system
    expire_stale_orders()

    with _get_connection() as conn:
        c = conn.cursor()

        # 2. Check plan validity
        c.execute("SELECT * FROM subscription_plans WHERE id = ? AND is_active = 1", (plan_id,))
        plan = c.fetchone()
        if not plan:
            return False, f"Tanlangan tarif ({plan_id}) mavjud emas yoki faol emas.", None

        # 3. Check active monitoring card
        card = get_active_monitoring_card()
        if not card:
            return False, "Hozirda to‘lovlarni qabul qiluvchi faol bank kartasi topilmadi. Ma’muriyatga murojaat qiling.", None

        now_dt = datetime.utcnow()
        now_str = now_dt.isoformat()

        # 4. Check user's current pending order
        c.execute("""
            SELECT * FROM payment_orders 
            WHERE user_id = ? AND status = 'PENDING'
            ORDER BY created_at DESC LIMIT 1
        """, (user_id,))
        existing_order = c.fetchone()

        if existing_order:
            exp_dt = datetime.fromisoformat(existing_order["expires_at"].replace("Z", ""))
            if now_dt < exp_dt:
                if existing_order["plan_id"] == plan_id:
                    # Scenario A: Same plan requested before expiration -> Reopen existing exact order
                    order_data = dict(existing_order)
                    diff = exp_dt - now_dt
                    order_data["remaining_seconds"] = max(0, int(diff.total_seconds()))
                    if card and card.get("card_number_encrypted"):
                        try:
                            raw = decrypt_data(card["card_number_encrypted"]).replace(" ", "")
                            order_data["card_number_raw"] = raw
                            if len(raw) == 16:
                                order_data["card_number_formatted"] = " ".join([raw[i:i+4] for i in range(0, 16, 4)])
                            else:
                                order_data["card_number_formatted"] = raw
                        except Exception:
                            order_data["card_number_raw"] = order_data.get("card_number_masked", "")
                            order_data["card_number_formatted"] = order_data.get("card_number_masked", "")
                    return True, "Amaldagi to‘lov buyurtmasi ochildi.", order_data
                else:
                    # Scenario B: Different plan requested before expiration -> Expire old order, create new
                    c.execute("UPDATE payment_orders SET status = 'EXPIRED' WHERE order_id = ?", (existing_order["order_id"],))
                    conn.commit()
            else:
                c.execute("UPDATE payment_orders SET status = 'EXPIRED' WHERE order_id = ?", (existing_order["order_id"],))
                conn.commit()

        # 5. Generate Unique Suffix (1 to 999 UZS) with retry protection against race condition
        base_price = plan["base_price_uzs"]
        max_retries = 5
        created_order_id = None

        for attempt in range(max_retries):
            # Refresh active amounts for this card
            c.execute("""
                SELECT final_amount_uzs FROM payment_orders 
                WHERE card_id = ? AND status = 'PENDING' AND expires_at > ?
            """, (card["id"], now_str))
            active_amounts = set(row[0] for row in c.fetchall())

            candidate_suffixes = list(range(1, 1000))
            secrets.SystemRandom().shuffle(candidate_suffixes)

            allocated_suffix = None
            for s in candidate_suffixes:
                candidate_amount = base_price + s
                if candidate_amount not in active_amounts:
                    allocated_suffix = s
                    break

            if allocated_suffix is None:
                return False, "To‘lov tizimi ayni paytda band. Iltimos, 1-2 daqiqadan so‘ng qayta urinib ko‘ring.", None

            final_amount = base_price + allocated_suffix
            order_id = f"ORD-{now_dt.strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(3).upper()}"
            expires_dt = now_dt + timedelta(minutes=ORDER_LIFETIME_MINUTES)
            expires_str = expires_dt.isoformat()

            try:
                # 6. Insert new payment order atomically
                c.execute("""
                    INSERT INTO payment_orders (
                        order_id, user_id, plan_id, plan_name, duration_days, base_price_uzs,
                        suffix_uzs, final_amount_uzs, card_id, card_suffix, card_number_masked,
                        cardholder_name, status, created_at, expires_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', ?, ?)
                """, (
                    order_id, user_id, plan["id"], plan["name"], plan["duration_days"],
                    base_price, allocated_suffix, final_amount, card["id"],
                    card["card_suffix"], card["card_number_masked"], card["cardholder_name"],
                    now_str, expires_str
                ))

                # 7. Record user activity event
                c.execute("""
                    INSERT INTO user_activity_events (user_id, event_name, event_data, created_at)
                    VALUES (?, 'PAYMENT_ORDER_CREATED', ?, ?)
                """, (user_id, f'{{"order_id": "{order_id}", "plan_id": "{plan_id}", "amount": {final_amount}}}', now_str))

                conn.commit()
                created_order_id = order_id
                break
            except sqlite3.IntegrityError:
                # Collision detected on concurrent insertion - retry with new suffix
                continue

        if not created_order_id:
            return False, "To‘lov tizimida ziddiyat yuz berdi. Iltimos, qayta urinib ko‘ring.", None

        order_id = created_order_id

        c.execute("SELECT * FROM payment_orders WHERE order_id = ?", (order_id,))
        created_order = dict(c.fetchone())
        created_order["remaining_seconds"] = ORDER_LIFETIME_MINUTES * 60
        if card and card.get("card_number_encrypted"):
            try:
                raw = decrypt_data(card["card_number_encrypted"]).replace(" ", "")
                created_order["card_number_raw"] = raw
                if len(raw) == 16:
                    created_order["card_number_formatted"] = " ".join([raw[i:i+4] for i in range(0, 16, 4)])
                else:
                    created_order["card_number_formatted"] = raw
            except Exception:
                created_order["card_number_raw"] = created_order.get("card_number_masked", "")
                created_order["card_number_formatted"] = created_order.get("card_number_masked", "")

        return True, "To‘lov uchun invoys yaratildi.", created_order
