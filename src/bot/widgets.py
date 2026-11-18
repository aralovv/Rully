"""
Telegram Interactive Widgets Layer (Bot API 10.4).
Builds lightweight, self-contained, sandboxed HTML widgets for progress and results visualization,
with automatic fallback to Rich Messages.
"""

import aiohttp
import json
import logging
from typing import Optional, Dict, Any
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, Message

logger = logging.getLogger(__name__)

def build_progress_widget_html(current: int, total: int, correct: int, incorrect: int) -> str:
    """
    Constructs a compact, self-contained HTML widget (<8KB) for visual exam progress.
    Complies with Telegram widget constraints: zero external network calls, pure inline CSS.
    """
    pct = int((current / total) * 100) if total > 0 else 0
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 12px; background: #1c242d; color: #ffffff; text-align: center; border-radius: 12px; }}
  .title {{ font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #8799a5; margin-bottom: 8px; }}
  .progress-bar-bg {{ background: #2b3642; border-radius: 8px; height: 12px; width: 100%; overflow: hidden; margin: 10px 0; }}
  .progress-fill {{ background: linear-gradient(90deg, #3390ec, #50a7ea); height: 100%; width: {pct}%; border-radius: 8px; transition: width 0.3s ease; }}
  .metrics {{ display: flex; justify-content: space-around; font-size: 14px; margin-top: 10px; }}
  .val-green {{ color: #4fae4e; font-weight: bold; }}
  .val-red {{ color: #e53935; font-weight: bold; }}
  .val-blue {{ color: #50a7ea; font-weight: bold; }}
</style>
</head>
<body>
  <div class="title">Avtotest Imtihon Jarayoni</div>
  <div class="progress-bar-bg">
    <div class="progress-fill"></div>
  </div>
  <div class="metrics">
    <div>Savol: <span class="val-blue">{current}/{total}</span></div>
    <div>To'g'ri: <span class="val-green">{correct}</span></div>
    <div>Xato: <span class="val-red">{incorrect}</span></div>
  </div>
</body>
</html>"""

def build_result_widget_html(total: int, correct: int, incorrect: int, passed: bool, percentage: float) -> str:
    """
    Constructs an interactive result badge widget.
    """
    status_color = "#4fae4e" if passed else "#e53935"
    status_text = "IMTIHONDAN O'TDI (СДАНО)" if passed else "YIQILDI (НЕ СДАНО)"
    
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 16px; background: #1c242d; color: #ffffff; text-align: center; border-radius: 14px; }}
  .badge {{ display: inline-block; padding: 6px 16px; border-radius: 20px; font-size: 14px; font-weight: 700; background: {status_color}; color: #ffffff; margin-bottom: 12px; }}
  .score {{ font-size: 32px; font-weight: 800; color: #ffffff; margin: 4px 0; }}
  .sub {{ font-size: 13px; color: #8799a5; margin-bottom: 12px; }}
  .stats-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 13px; text-align: left; background: #232d38; padding: 10px; border-radius: 8px; }}
</style>
</head>
<body>
  <div class="badge">{status_text}</div>
  <div class="score">{percentage}%</div>
  <div class="sub">{correct} / {total} to'g'ri javob</div>
  <div class="stats-grid">
    <div>To'g'ri: <b style="color: #4fae4e;">{correct}</b></div>
    <div>Xatolar: <b style="color: #e53935;">{incorrect}</b></div>
    <div>O'tish balli: <b>18 ta</b></div>
    <div>Format: <b>20 savol / 25 daq</b></div>
  </div>
</body>
</html>"""

async def send_native_widget_or_fallback(bot: Bot, chat_id: int, widget_html: str,
                                         fallback_text: str, reply_markup: Optional[InlineKeyboardMarkup] = None) -> Message:
    """
    Attempts to deliver via Telegram Bot API 10.4 `sendWidget` method.
    If unsupported or client rejected, gracefully falls back to Rich HTML Message.
    """
    url = f"https://api.telegram.org/bot{bot.token}/sendWidget"
    payload = {
        "chat_id": chat_id,
        "widget": widget_html
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup.model_dump(exclude_none=True)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=3.0)) as resp:
                data = await resp.json()
                if resp.status == 200 and data.get("ok"):
                    logger.info(f"Widget successfully sent to chat {chat_id}")
                    # Return sent message representation if needed
                    return data["result"]
    except Exception as e:
        logger.debug(f"sendWidget call returned: {e}. Falling back to Rich Message.")

    # Graceful standard fallback to Rich Message
    return await bot.send_message(
        chat_id=chat_id,
        text=fallback_text,
        parse_mode="HTML",
        reply_markup=reply_markup
    )
