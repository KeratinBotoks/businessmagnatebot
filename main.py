import asyncio
import logging
import sys
from pathlib import Path

# Добавляем текущую директорию в путь
sys.path.append(str(Path(__file__).parent))

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

# Импортируем нашу конфигурацию
try:
    from config import config, BOT_TOKEN
except ImportError as e:
    print(f"❌ Ошибка импорта config.py: {e}")
    print("Убедитесь, что файл config.py существует в той же директории")
    sys.exit(1)

# Проверяем токен бота
if not BOT_TOKEN:
    print("❌ ОШИБКА: BOT_TOKEN не установлен!")
    print("Добавьте BOT_TOKEN в переменные окружения или в файл .env")
    sys.exit(1)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/bot.log", encoding="utf-8")
    ]
)
logger = logging.getLogger(__name__)

async def set_bot_commands(bot: Bot):
    """Установка команд бота"""
    commands = [
        BotCommand(command="/start", description="🚀 Запустить игру"),
        BotCommand(command="/profile", description="👤 Мой профиль"),
        BotCommand(command="/business", description="🏢 Мои бизнесы"),
        BotCommand(command="/stocks", description="📊 Фондовая биржа"),
        BotCommand(command="/players", description="🤝 Игроки"),
        BotCommand(command="/help", description="❓ Помощь"),
    ]
    await bot.set_my_commands(commands)

async def main():
    """Основная функция запуска бота"""
    
    # Создаем необходимые директории
    Path("data").mkdir(exist_ok=True)
    Path("logs").mkdir(exist_ok=True)
    Path("configs").mkdir(exist_ok=True)
    
    # Инициализация базы данных
    try:
        from database.database import db
        db.init_db()
        logger.info("✅ База данных инициализирована")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации БД: {e}")
        return
    
    # Инициализация бота
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    
    # Регистрация обработчиков
    try:
        from handlers import register_handlers
        register_handlers(dp)
        logger.info("✅ Обработчики зарегистрированы")
    except Exception as e:
        logger.error(f"❌ Ошибка регистрации обработчиков: {e}")
    
    # Установка команд бота
    await set_bot_commands(bot)
    
    # Инициализация акций
    try:
        from services.stock_service import StockService
        with db.get_session() as session:
            stock_service = StockService()
            stock_service.init_stocks(session)
            logger.info("✅ Акции инициализированы")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации акций: {e}")
    
    # Запуск планировщика
    try:
        from services.scheduler_service import SchedulerService
        scheduler = SchedulerService(bot)
        scheduler.start()
        logger.info("✅ Планировщик задач запущен")
    except Exception as e:
        logger.error(f"❌ Ошибка запуска планировщика: {e}")
    
    # Запуск бота
    logger.info("🚀 Бот запущен и готов к работе!")
    logger.info(f"🤖 ID администраторов: {config.ADMIN_IDS}")
    
    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("⏹️ Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
    finally:
        await bot.session.close()
        logger.info("👋 Бот завершил работу")

if __name__ == "__main__":
    # Проверяем Python версию
    if sys.version_info < (3, 10):
        print("❌ Требуется Python 3.10 или выше")
        sys.exit(1)
    
    # Запускаем бота
    asyncio.run(main())