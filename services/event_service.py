import json
from typing import Dict, List, Optional
from sqlalchemy.orm import Session # type: ignore
from aiogram import Bot
from models.transaction import Transaction
from models.user import User
from database.database import db
from config import config

class EventService:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.events_config = self._load_events_config()
    
    def _load_events_config(self) -> Dict:
        """Загрузка конфигурации событий"""
        try:
            with open(config.EVENTS_CONFIG, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {"events": {}}
    
    async def publish_large_transaction(self, transaction: Transaction):
        """Публикация информации о крупной сделке"""
        try:
            with db.get_session() as session:
                user = session.query(User).filter(User.id == transaction.user_id).first()
                if not user:
                    return
                
                amount = abs(transaction.amount)
                transaction_type = transaction.transaction_type
                
                # Определяем тип события
                if transaction_type in ['buy_business', 'upgrade_business']:
                    event_config = self.events_config.get('events', {}).get('business_purchase', {})
                    min_amount = event_config.get('min_amount', 10000)
                    
                    if amount >= min_amount:
                        details = transaction.details or {}
                        business_name = details.get('business_name', 'Неизвестный бизнес')
                        
                        message = event_config.get('message_template', 
                            "🎉 КРУПНАЯ СДЕЛКА!\n\n👤 Игрок: {username}\n💼 Тип: {type}\n💰 Сумма: ${amount:,.2f}")
                        
                        formatted = message.format(
                            username=user.username or user.full_name or f"Игрок_{user.id}",
                            type="Покупка бизнеса" if transaction_type == 'buy_business' else "Улучшение бизнеса",
                            business_name=business_name,
                            amount=amount
                        )
                        
                        await self._send_to_channel(formatted)
                
                elif transaction_type in ['buy_stock', 'sell_stock']:
                    event_config = self.events_config.get('events', {}).get('stock_purchase', {})
                    min_amount = event_config.get('min_amount', 5000)
                    
                    if amount >= min_amount:
                        details = transaction.details or {}
                        stock_name = details.get('stock_name', 'Неизвестная акция')
                        
                        message = event_config.get('message_template',
                            "📈 КРУПНАЯ СДЕЛКА С АКЦИЯМИ!\n\n👤 Игрок: {username}\n🏦 Акция: {stock_name}\n💼 Тип: {type}\n💰 Сумма: ${amount:,.2f}")
                        
                        formatted = message.format(
                            username=user.username or user.full_name or f"Игрок_{user.id}",
                            stock_name=stock_name,
                            type="Покупка" if transaction_type == 'buy_stock' else "Продажа",
                            amount=amount
                        )
                        
                        await self._send_to_channel(formatted)
        
        except Exception as e:
            print(f"Error publishing transaction event: {e}")
    
    async def publish_level_up(self, user: User, new_level: int):
        """Публикация информации о повышении уровня"""
        try:
            event_config = self.events_config.get('events', {}).get('level_up', {})
            min_level = event_config.get('min_level', 10)
            
            if new_level >= min_level:
                message = event_config.get('message_template',
                    "🚀 НОВЫЙ УРОВЕНЬ!\n\n👤 Игрок: {username}\n🎯 Достиг уровня: {level}")
                
                formatted = message.format(
                    username=user.username or user.full_name or f"Игрок_{user.id}",
                    level=new_level
                )
                
                await self._send_to_channel(formatted)
        
        except Exception as e:
            print(f"Error publishing level up event: {e}")
    
    async def _send_to_channel(self, message: str):
        """Отправка сообщения в канал"""
        try:
            if config.CHANNEL_ID:
                await self.bot.send_message(config.CHANNEL_ID, message)
        except Exception as e:
            print(f"Error sending to channel: {e}")