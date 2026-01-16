import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import config
from database.database import db
from services.scheduler_service import SchedulerService
from services.stock_service import StockService

# Импорт handlers
from handlers import start, profile, business, stock_market, players, admin, errors

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """Основная функция запуска бота"""
    
    # Инициализация базы данных
    db.init_db()
    
    # Инициализация бота и диспетчера
    bot = Bot(token=config.BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Включаем обработчики
    dp.include_router(start.router)
    dp.include_router(profile.router)
    dp.include_router(business.router)
    dp.include_router(stock_market.router)
    dp.include_router(players.router)
    dp.include_router(admin.router)
    dp.include_router(errors.router)
    
    # Инициализация акций
    with db.get_session() as session:
        stock_service = StockService()
        stock_service.init_stocks(session)
    
    # Запуск планировщика задач
    scheduler_service = SchedulerService(bot)
    scheduler_service.start()
    
    # Запуск бота
    logger.info("Бот запущен!")
    
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())