"""
Bot Handlers Package.
"""
from aiogram import Router
from src.bot.handlers.start import start_router
from src.bot.handlers.menu import menu_router
from src.bot.handlers.quiz import quiz_router
from src.bot.handlers.exam import exam_router
from src.bot.handlers.custom_test import custom_test_router
from src.bot.handlers.practice import practice_router
from src.bot.handlers.mistakes import mistakes_router
from src.bot.handlers.results import results_router
from src.bot.handlers.admin import admin_router

main_router = Router(name="main_router")

# Include all subrouters in logical priority order
main_router.include_router(start_router)
main_router.include_router(menu_router)
main_router.include_router(exam_router)
main_router.include_router(custom_test_router)
main_router.include_router(practice_router)
main_router.include_router(mistakes_router)
main_router.include_router(results_router)
main_router.include_router(admin_router)
main_router.include_router(quiz_router) # Quiz callbacks
