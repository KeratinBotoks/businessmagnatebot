from aiogram import Bot
from typing import List, Dict
from config import config

class ChannelService:
    def __init__(self, bot: Bot):
        self.bot = bot
    
    async def publish_to_channel(self, message: str):
        """Публикация сообщения в канал"""
        try:
            if config.CHANNEL_ID:
                await self.bot.send_message(config.CHANNEL_ID, message)
                return True
            return False
        except Exception as e:
            print(f"Error publishing to channel: {e}")
            return False
    
    async def publish_lottery_results(self, winners: List[Dict]):
        """Публикация результатов розыгрыша"""
        if not winners:
            return
        
        message = "🎉 РЕЗУЛЬТАТЫ ЕЖЕНЕДЕЛЬНОГО РОЗЫГРЫША\n\n"
        
        for i, winner_info in enumerate(winners, 1):
            user = winner_info['user']
            message += f"{i}. @{user.username or user.full_name or f'Игрок_{user.id}'}\n"
            message += f"   Приз: {winner_info['prize']}\n"
            message += f"   Сумма: ${winner_info['amount']:,.2f}\n\n"
        
        message += "Поздравляем победителей! 🎊"
        
        await self.publish_to_channel(message)
    
    async def publish_achievement(self, username: str, achievement_name: str, description: str):
        """Публикация достижения"""
        message = (
            f"🏆 НОВОЕ ДОСТИЖЕНИЕ!\n\n"
            f"👤 Игрок: @{username}\n"
            f"🎯 Достижение: {achievement_name}\n"
            f"📝 Описание: {description}\n\n"
            f"Поздравляем! 👏"
        )
        
        await self.publish_to_channel(message)