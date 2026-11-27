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
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from src.admin.deps import get_current_admin, require_admin_role
from src.security.telegram_notifier import send_telegram_message, MAIN_BOT_TOKEN

router = APIRouter(
    prefix="/api/admin/broadcast",
    tags=["Admin Broadcast"],
    dependencies=[Depends(require_admin_role("SUPERADMIN"))],
)
DB_PATH = os.getenv("DB_PATH", "master_database.sqlite")


from src.db_adapter import get_db_connection

def _get_connection():
    return get_db_connection(DB_PATH)


class BroadcastMessageRequest(BaseModel):
    message_text: Optional[str] = Field(None, max_length=4000, description="Broadcast message text with optional HTML tags")
    message: Optional[str] = Field(None, max_length=4000, description="Frontend-compatible alias for message_text")
    target_group: str = Field("all", description="Target group: 'all', 'pro', or 'free'")

    def resolved_message(self) -> str:
        return (self.message_text if self.message_text is not None else (self.message or "")).strip()


@router.get("/audience")
def get_broadcast_audience(current_admin: dict = Depends(get_current_admin)):
    """Returns recipient counts for different target segments."""
    now_iso = datetime.utcnow().isoformat()
    with _get_connection() as conn:
        c = conn.cursor()
        c.execute(
            """
            SELECT 
                COUNT(*) as total_users,
                SUM(CASE WHEN is_pro = 1 AND subscription_expires_at > ? THEN 1 ELSE 0 END) as pro_users,
                SUM(CASE WHEN is_pro = 0 OR subscription_expires_at <= ? OR subscription_expires_at IS NULL THEN 1 ELSE 0 END) as free_users
            FROM telegram_users
            WHERE is_blocked = 0
            """,
            (now_iso, now_iso),
        )
        row = c.fetchone()
        return {
            "ok": True,
            "counts": {
                "all": row["total_users"] or 0,
                "pro": row["pro_users"] or 0,
                "free": row["free_users"] or 0
            }
        }


def _log_broadcast_audit_sync(admin_id: int, audit_details: str, now_str: str):
    with _get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            INSERT INTO admin_audit_logs (admin_id, action, details, performed_at)
            VALUES (?, 'BROADCAST_SENT', ?, ?)
        """, (admin_id, audit_details, now_str))
        conn.commit()


async def _execute_broadcast_task(users: List[Dict[str, Any]], clean_text: str, target: str, admin_id: int, admin_username: str):
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

    # Create administrative audit record off the event loop
    now_str = datetime.utcnow().isoformat()
    audit_details = json.dumps({
        "target_group": target,
        "total_targets": len(users),
        "sent_count": sent_count,
        "failed_count": failed_count,
        "sent": sent_count,
        "failed": failed_count,
        "message_snippet": clean_text[:120] + ("..." if len(clean_text) > 120 else ""),
        "admin_username": admin_username
    }, ensure_ascii=False)

    try:
        await asyncio.to_thread(_log_broadcast_audit_sync, admin_id, audit_details, now_str)
    except Exception:
        pass


@router.post("")
@router.post("/send")
def send_broadcast_message(
    req: BroadcastMessageRequest,
    background_tasks: BackgroundTasks,
    current_admin: dict = Depends(get_current_admin)
):
    """
    Dispatches a broadcast message to the selected target audience in Telegram.
    Runs asynchronously via BackgroundTasks to eliminate HTTP timeouts.
    """
    target = req.target_group.lower().strip()
    if target not in ("all", "pro", "free"):
        raise HTTPException(status_code=400, detail="Noto‘g‘ri maqsadli guruh: 'all', 'pro', yoki 'free' bo‘lishi lozim.")

    clean_text = req.resolved_message()
    if not clean_text:
        raise HTTPException(status_code=400, detail="Xabar matni bo‘sh bo‘lishi mumkin emas.")
    if len(clean_text) > 4000:
        raise HTTPException(status_code=400, detail="Xabar matni 4000 belgidan oshmasligi kerak.")

    now_iso = datetime.utcnow().isoformat()
    # 1. Fetch targeted recipients
    with _get_connection() as conn:
        c = conn.cursor()
        if target == "pro":
            c.execute(
                """
                SELECT user_id, first_name FROM telegram_users 
                WHERE is_blocked = 0 AND is_pro = 1 AND subscription_expires_at > ?
                """,
                (now_iso,),
            )
        elif target == "free":
            c.execute(
                """
                SELECT user_id, first_name FROM telegram_users 
                WHERE is_blocked = 0 AND (is_pro = 0 OR subscription_expires_at <= ? OR subscription_expires_at IS NULL)
                """,
                (now_iso,),
            )
        else:  # all
            c.execute("SELECT user_id, first_name FROM telegram_users WHERE is_blocked = 0")
        
        users = [dict(r) for r in c.fetchall()]

    if not users:
        return {
            "ok": True,
            "total_targets": 0,
            "sent_count": 0,
            "failed_count": 0,
            "sent": 0,
            "failed": 0,
            "message": "Tanlangan guruhda faol foydalanuvchilar topilmadi."
        }

    # 2. Queue background broadcast task
    background_tasks.add_task(
        _execute_broadcast_task,
        users=users,
        clean_text=clean_text,
        target=target,
        admin_id=current_admin.get("id", current_admin.get("admin_id", 1)),
        admin_username=current_admin.get("username", "Admin")
    )

    return {
        "ok": True,
        "total_targets": len(users),
        "sent_count": len(users),
        "failed_count": 0,
        "message": f"Xabarnoma yuborilmoqda: {len(users)} ta foydalanuvchiga fonda yetkazilmoqda."
    }


@router.get("/history")
def get_broadcast_history(
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
            meta: Dict[str, Any] = {}
            if r.get("details"):
                try:
                    meta = json.loads(r["details"]) or {}
                except Exception:
                    meta = {}
            sent_val = meta.get("sent", meta.get("sent_count", 0))
            failed_val = meta.get("failed", meta.get("failed_count", 0))
            meta["sent"] = sent_val
            meta["sent_count"] = sent_val
            meta["failed"] = failed_val
            meta["failed_count"] = failed_val
            r["meta"] = meta
        return {
            "ok": True,
            "history": rows
        }
