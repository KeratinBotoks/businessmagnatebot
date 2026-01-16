from aiogram import Dispatcher
from .start import router as start_router
from .profile import router as profile_router
from .business import router as business_router
from .stock_market import router as stock_market_router
from .players import router as players_router
from .admin import router as admin_router
from .errors import router as errors_router

def register_handlers(dp: Dispatcher):
    """Регистрация всех обработчиков"""
    dp.include_router(start_router)
    dp.include_router(profile_router)
    dp.include_router(business_router)
    dp.include_router(stock_market_router)
    dp.include_router(players_router)
    dp.include_router(admin_router)
    dp.include_router(errors_router)