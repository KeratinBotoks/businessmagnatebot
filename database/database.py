from sqlalchemy import create_engine # type: ignore
from sqlalchemy.orm import sessionmaker # type: ignore
from .models import Base
from config import config
import os

class Database:
    def __init__(self):
        self.engine = create_engine(config.DATABASE_URL)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def init_db(self):
        """Инициализация базы данных и создание таблиц"""
        # Создаем директорию для данных, если её нет
        os.makedirs("data", exist_ok=True)
        
        Base.metadata.create_all(bind=self.engine)
        print("Database tables created successfully")
    
    def get_session(self):
        """Получение сессии базы данных"""
        return self.SessionLocal()

db = Database()