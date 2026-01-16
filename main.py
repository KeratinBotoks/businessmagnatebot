import asyncio
import logging
import sys
from pathlib import Path

# Добавляем текущую директорию в путь для импортов
sys.path.append(str(Path(__file__).parent))

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import config
from database.database import db
from services.scheduler_service import SchedulerService

# Импорт handlers
from handlers.start import router as start_router
from handlers.profile import router as profile_router
from handlers.business import router as business_router
from handlers.stock_market import router as stock_market_router
from handlers.players import router as players_router
from handlers.admin import router as admin_router

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

async def main():
    """Основная функция запуска бота"""
    
    # Проверка токена бота
    if not config.BOT_TOKEN:
        logger.error("BOT_TOKEN не найден в переменных окружения")
        return
    
    # Инициализация базы данных
    db.init_db()
    
    # Инициализация бота и диспетчера
    bot = Bot(token=config.BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Включаем обработчики
    dp.include_router(start_router)
    dp.include_router(profile_router)
    dp.include_router(business_router)
    dp.include_router(stock_market_router)
    dp.include_router(players_router)
    dp.include_router(admin_router)
    
    # Запуск планировщика задач
    scheduler_service = SchedulerService(bot)
    scheduler_service.start()
    
    # Запуск бота
    logger.info("Бот запущен!")
    
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    # Создаем необходимые директории
    Path("data").mkdir(exist_ok=True)
    Path("logs").mkdir(exist_ok=True)
    Path("configs").mkdir(exist_ok=True)
    
    asyncio.run(main())