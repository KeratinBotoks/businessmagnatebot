import os
from dataclasses import dataclass
from dotenv import load_dotenv # type: ignore

load_dotenv()

@dataclass
class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN")
    ADMIN_IDS: list = list(map(int, os.getenv("ADMIN_IDS", "").split(','))) if os.getenv("ADMIN_IDS") else []
    CHANNEL_ID: str = os.getenv("CHANNEL_ID", "")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///data/database.db")
    
    # Игровые константы
    STARTING_BALANCE: float = 1000.0
    TAX_RATE: float = 0.05  # 5% налог на транзакции
    DAILY_BONUS_BASE: float = 100.0
    MAX_BUSINESSES_PER_USER: int = 10
    STOCK_UPDATE_INTERVAL_MINUTES: int = 15
    
    # Пути к конфигурационным файлам
    BUSINESSES_CONFIG: str = "configs/businesses.json"
    STOCKS_CONFIG: str = "configs/stocks.json"
    LEVELS_CONFIG: str = "configs/levels.json"

config = Config()