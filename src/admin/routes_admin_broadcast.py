"""
Admin Broadcast Messaging System.
Allows administrators to send announcements and updates to Telegram users:
- Target groups: All users, Free users only, PRO subscribers only
- Safe rate limiting adhering to Telegram's 30 msgs/second ceiling
- Robust error tolerance for blocked/deactivated users
- Full administrative audit logging
"""

import os
import sqlite3
import json
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.admin.deps import get_current_admin
from src.security.telegram_notifier import send_telegram_message, MAIN_BOT_TOKEN

router = APIRouter(prefix="/api/admin/broadcast", tags=["Admin Broadcast"])
DB_PATH = os.getenv("DB_PATH", "master_database.sqlite")


def _get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


class BroadcastMessageRequest(BaseModel):
    message_text: str = Field(..., min_length=1, max_length=4000, description="Broadcast message text with optional HTML tags")
    target_group: str = Field("all", description="Target group: 'all', 'pro', or 'free'")


@router.get("/audience")
async def get_broadcast_audience(current_admin: dict = Depends(get_current_admin)):
    """Returns recipient counts for different target segments."""
    with _get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT 
                COUNT(*) as total_users,
                SUM(CASE WHEN is_pro = 1 AND subscription_expires_at > datetime('now') THEN 1 ELSE 0 END) as pro_users,
                SUM(CASE WHEN is_pro = 0 OR subscription_expires_at <= datetime('now') OR subscription_expires_at IS NULL THEN 1 ELSE 0 END) as free_users
            FROM telegram_users
            WHERE is_blocked = 0
        """)
        row = c.fetchone()
        return {
            "ok": True,
            "counts": {
                "all": row["total_users"] or 0,
                "pro": row["pro_users"] or 0,
                "free": row["free_users"] or 0
            }
        }


@router.post("")
async def send_broadcast_message(
    req: BroadcastMessageRequest,
    current_admin: dict = Depends(get_current_admin)
):
    """
    Dispatches a broadcast message to the selected target audience in Telegram.
    Enforces rate limiting (~25 msgs/sec) and logs the action in audit records.
    """
    target = req.target_group.lower().strip()
    if target not in ("all", "pro", "free"):
        raise HTTPException(status_code=400, detail="Noto‘g‘ri maqsadli guruh: 'all', 'pro', yoki 'free' bo‘lishi lozim.")

    clean_text = req.message_text.strip()
    if not clean_text:
        raise HTTPException(status_code=400, detail="Xabar matni bo‘sh bo‘lishi mumkin emas.")

    # 1. Fetch targeted recipients
    with _get_connection() as conn:
        c = conn.cursor()
        if target == "pro":
            c.execute("""
                SELECT user_id, first_name FROM telegram_users 
                WHERE is_blocked = 0 AND is_pro = 1 AND subscription_expires_at > datetime('now')
            """)
        elif target == "free":
            c.execute("""
                SELECT user_id, first_name FROM telegram_users 
                WHERE is_blocked = 0 AND (is_pro = 0 OR subscription_expires_at <= datetime('now') OR subscription_expires_at IS NULL)
            """)
        else:  # all
            c.execute("SELECT user_id, first_name FROM telegram_users WHERE is_blocked = 0")
        
        users = [dict(r) for r in c.fetchall()]

    if not users:
        return {
            "ok": True,
            "total_targets": 0,
            "sent_count": 0,
            "failed_count": 0,
            "message": "Tanlangan guruhda faol foydalanuvchilar topilmadi."
        }

    # 2. Iterate and send with rate limiting
    sent_count = 0
    failed_count = 0

    for user in users:
        uid = user["user_id"]
        try:
            success = await send_telegram_message(
                bot_token=MAIN_BOT_TOKEN,
                chat_id=uid,
                text=clean_text,
                parse_mode="HTML"
            )
            if success:
                sent_count += 1
            else:
                failed_count += 1
        except Exception:
            failed_count += 1

        # Rate-limiting pause (Telegram ceiling: 30 msgs/sec -> 0.04s ≈ 25 msgs/sec)
        await asyncio.sleep(0.04)

    # 3. Create administrative audit record
    now_str = datetime.utcnow().isoformat()
    audit_details = json.dumps({
        "target_group": target,
        "total_targets": len(users),
        "sent_count": sent_count,
        "failed_count": failed_count,
        "message_snippet": clean_text[:120] + ("..." if len(clean_text) > 120 else ""),
        "admin_username": current_admin.get("username", "Anvarjon")
    }, ensure_ascii=False)

    with _get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            INSERT INTO admin_audit_logs (admin_id, action, details, performed_at)
            VALUES (?, 'BROADCAST_SENT', ?, ?)
        """, (current_admin.get("admin_id", 1), audit_details, now_str))
        conn.commit()

    return {
        "ok": True,
        "total_targets": len(users),
        "sent_count": sent_count,
        "failed_count": failed_count,
        "message": f"Xabarnoma yuborildi: {sent_count} ta yetkazildi, {failed_count} ta yetkazilmadi."
    }


@router.get("/history")
async def get_broadcast_history(
    limit: int = 10,
    current_admin: dict = Depends(get_current_admin)
):
    """Retrieves recent broadcast audit logs."""
    with _get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT * FROM admin_audit_logs 
            WHERE action = 'BROADCAST_SENT' 
            ORDER BY id DESC LIMIT ?
        """, (limit,))
        rows = [dict(r) for r in c.fetchall()]
        for r in rows:
            if r.get("details"):
                try:
                    r["meta"] = json.loads(r["details"])
                except Exception:
                    r["meta"] = {}
        return {
            "ok": True,
            "history": rows
        }
