import os

# Простой config без dataclass
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# ADMIN_IDS как список
admin_ids_str = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = []
if admin_ids_str:
    ADMIN_IDS = [int(x.strip()) for x in admin_ids_str.split(',') if x.strip()]

CHANNEL_ID = os.getenv("CHANNEL_ID", "")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data/database.db")

# Константы
STARTING_BALANCE = 1000.0
TAX_RATE = 0.05
DAILY_BONUS_BASE = 100.0
MAX_BUSINESSES_PER_USER = 10
STOCK_UPDATE_INTERVAL_MINUTES = 15

BUSINESSES_CONFIG = "configs/businesses.json"
STOCKS_CONFIG = "configs/stocks.json"
LEVELS_CONFIG = "configs/levels.json"
EVENTS_CONFIG = "configs/events.json"
BONUSES_CONFIG = "configs/bonuses.json"

# Объект config для обратной совместимости
class Config:
    pass

config = Config()
config.BOT_TOKEN = BOT_TOKEN
config.ADMIN_IDS = ADMIN_IDS
config.CHANNEL_ID = CHANNEL_ID
config.DATABASE_URL = DATABASE_URL
config.STARTING_BALANCE = STARTING_BALANCE
config.TAX_RATE = TAX_RATE
config.DAILY_BONUS_BASE = DAILY_BONUS_BASE
config.MAX_BUSINESSES_PER_USER = MAX_BUSINESSES_PER_USER
config.STOCK_UPDATE_INTERVAL_MINUTES = STOCK_UPDATE_INTERVAL_MINUTES
config.BUSINESSES_CONFIG = BUSINESSES_CONFIG
config.STOCKS_CONFIG = STOCKS_CONFIG
config.LEVELS_CONFIG = LEVELS_CONFIG
config.EVENTS_CONFIG = EVENTS_CONFIG
config.BONUSES_CONFIG = BONUSES_CONFIG