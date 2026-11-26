"""
Bot Middlewares: User Registration, Database Dependency Injection, and Rate Limiting.
"""
import asyncio
import time
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User
from src.bot.database import BotDatabase
from src.avtotest_product import AvtotestProductEngine

class DependencyInjectionMiddleware(BaseMiddleware):
    def __init__(self, db: BotDatabase, product_engine: AvtotestProductEngine):
        super().__init__()
        self.db = db
        self.product_engine = product_engine

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        data["db"] = self.db
        data["product_engine"] = self.product_engine

        # User tracking & block enforcement off the event loop
        event_user: User = data.get("event_from_user")
        if event_user and not event_user.is_bot:
            db_user = await asyncio.to_thread(
                self.db.get_or_create_user,
                user_id=event_user.id,
                username=event_user.username,
                first_name=event_user.first_name,
                last_name=event_user.last_name
            )
            if isinstance(db_user, dict) and int(db_user.get("is_blocked") or 0) == 1:
                return None

        return await handler(event, data)


class SimpleRateLimitMiddleware(BaseMiddleware):
    """
    Lightweight rate limiter preventing fast button spamming.
    """
    def __init__(self, limit_seconds: float = 0.2):
        super().__init__()
        self.limit = limit_seconds
        self.user_timestamps: Dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        event_user: User = data.get("event_from_user")
        if event_user:
            now = time.time()
            last_time = self.user_timestamps.get(event_user.id, 0.0)
            if now - last_time < self.limit:
                # Silently throttle
                return None
            self.user_timestamps[event_user.id] = now

        return await handler(event, data)
