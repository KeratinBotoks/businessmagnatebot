from aiogram import Router
from aiogram.types import ErrorEvent
import logging

router = Router()

@router.error()
async def error_handler(event: ErrorEvent):
    """Обработчик ошибок"""
    logging.error(f"Ошибка: {event.exception}", exc_info=True)