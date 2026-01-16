import os
from typing import List

# ====================
# ЗАГРУЗКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ
# ====================

# Токен бота (обязательно)
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
if not BOT_TOKEN:
    print("⚠️ ВНИМАНИЕ: BOT_TOKEN не установлен!")

# ID администраторов (через запятую)
ADMIN_IDS_STR = os.getenv("ADMIN_IDS", "")
ADMIN_IDS: List[int] = []
if ADMIN_IDS_STR:
    for admin_id in ADMIN_IDS_STR.split(','):
        admin_id = admin_id.strip()
        if admin_id:
            try:
                ADMIN_IDS.append(int(admin_id))
            except ValueError:
                print(f"⚠️ Ошибка парсинга ADMIN_ID: {admin_id}")

# ID канала для публикации событий
CHANNEL_ID = os.getenv("CHANNEL_ID", "")

# URL базы данных
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data/database.db")

# ====================
# ИГРОВЫЕ КОНСТАНТЫ
# ====================

# Начальный баланс нового игрока
STARTING_BALANCE = 1000.0

# Налог на транзакции (5%)
TAX_RATE = 0.05

# Базовый ежедневный бонус
DAILY_BONUS_BASE = 100.0

# Максимум бизнесов у одного пользователя
MAX_BUSINESSES_PER_USER = 10

# Интервал обновления цен акций (в минутах)
STOCK_UPDATE_INTERVAL_MINUTES = 15

# ====================
# ПУТИ К КОНФИГУРАЦИОННЫМ ФАЙЛАМ
# ====================

BUSINESSES_CONFIG = "configs/businesses.json"
STOCKS_CONFIG = "configs/stocks.json"
LEVELS_CONFIG = "configs/levels.json"
EVENTS_CONFIG = "configs/events.json"
BONUSES_CONFIG = "configs/bonuses.json"

# ====================
# КЛАСС ДЛЯ ОБРАТНОЙ СОВМЕСТИМОСТИ
# ====================

class ConfigClass:
    """Класс для обратной совместимости с существующим кодом"""
    def __init__(self):
        self.BOT_TOKEN = BOT_TOKEN
        self.ADMIN_IDS = ADMIN_IDS
        self.CHANNEL_ID = CHANNEL_ID
        self.DATABASE_URL = DATABASE_URL
        self.STARTING_BALANCE = STARTING_BALANCE
        self.TAX_RATE = TAX_RATE
        self.DAILY_BONUS_BASE = DAILY_BONUS_BASE
        self.MAX_BUSINESSES_PER_USER = MAX_BUSINESSES_PER_USER
        self.STOCK_UPDATE_INTERVAL_MINUTES = STOCK_UPDATE_INTERVAL_MINUTES
        self.BUSINESSES_CONFIG = BUSINESSES_CONFIG
        self.STOCKS_CONFIG = STOCKS_CONFIG
        self.LEVELS_CONFIG = LEVELS_CONFIG
        self.EVENTS_CONFIG = EVENTS_CONFIG
        self.BONUSES_CONFIG = BONUSES_CONFIG

# Глобальный экземпляр конфигурации
config = ConfigClass()