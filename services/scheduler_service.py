from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
from sqlalchemy.orm import Session # type: ignore
from database.database import db
from services.stock_service import StockService
from services.event_service import EventService
from services.channel_service import ChannelService
import asyncio

class SchedulerService:
    def __init__(self, bot):
        self.bot = bot
        self.scheduler = AsyncIOScheduler()
        self.stock_service = StockService()
        self.event_service = EventService()
        self.channel_service = ChannelService(bot)
    
    def start(self):
        """Запуск всех планировщиков"""
        # Обновление цен акций каждые 15 минут
        self.scheduler.add_job(
            self.update_stock_prices,
            IntervalTrigger(minutes=15),
            id='update_stocks'
        )
        
        # Ежедневная статистика для админов в 00:00
        self.scheduler.add_job(
            self.send_daily_stats,
            CronTrigger(hour=0, minute=0),
            id='daily_stats'
        )
        
        # Еженедельный розыгрыш в воскресенье в 20:00
        self.scheduler.add_job(
            self.weekly_lottery,
            CronTrigger(day_of_week='sun', hour=20, minute=0),
            id='weekly_lottery'
        )
        
        # Ежечасное обновление событий
        self.scheduler.add_job(
            self.check_events,
            IntervalTrigger(hours=1),
            id='check_events'
        )
        
        # Публикация топ игроков в канал каждый день в 12:00
        self.scheduler.add_job(
            self.publish_top_players,
            CronTrigger(hour=12, minute=0),
            id='publish_top_players'
        )
        
        self.scheduler.start()
        print("Scheduler started successfully")
    
    async def update_stock_prices(self):
        """Обновление цен акций"""
        try:
            with db.get_session() as session:
                self.stock_service.update_stock_prices(session)
                print(f"Stock prices updated at {datetime.utcnow()}")
        except Exception as e:
            print(f"Error updating stock prices: {e}")
    
    async def send_daily_stats(self):
        """Отправка ежедневной статистики админам"""
        try:
            from config import config
            from services.economy_service import EconomyService
            
            economy_service = EconomyService()
            
            with db.get_session() as session:
                stats = economy_service.get_economy_stats(session)
                
                message = "📊 ЕЖЕДНЕВНАЯ СТАТИСТИКА\n\n"
                message += f"👥 Всего пользователей: {stats['total_users']}\n"
                message += f"🎯 Активных за 24ч: {stats['active_users_24h']}\n"
                message += f"💰 Общий баланс: ${stats['total_balance']:,.2f}\n"
                message += f"📈 Всего заработано: ${stats['total_earned']:,.2f}\n"
                message += f"📉 Всего потрачено: ${stats['total_spent']:,.2f}\n"
                message += f"🔄 Транзакций за 24ч: {stats['transactions_24h']}\n\n"
                message += "🏆 ТОП-5 ИГРОКОВ:\n"
                
                for i, user in enumerate(stats['top_users'], 1):
                    message += f"{i}. @{user['username']} - ${user['balance']:,.2f} (уровень {user['level']})\n"
                
                # Отправляем всем админам
                for admin_id in config.ADMIN_IDS:
                    try:
                        await self.bot.send_message(admin_id, message)
                    except Exception as e:
                        print(f"Error sending stats to admin {admin_id}: {e}")
                
                print(f"Daily stats sent at {datetime.utcnow()}")
        
        except Exception as e:
            print(f"Error in send_daily_stats: {e}")
    
    async def weekly_lottery(self):
        """Проведение еженедельного розыгрыша"""
        try:
            from config import config
            from models.user import User
            import random
            
            with db.get_session() as session:
                # Получаем всех активных пользователей (за последнюю неделю)
                week_ago = datetime.utcnow() - timedelta(days=7) # type: ignore
                active_users = session.query(User).filter(
                    User.last_daily >= week_ago
                ).all()
                
                if not active_users:
                    print("No active users for lottery")
                    return
                
                # Выбираем победителей
                prizes = [
                    {"name": "Главный приз", "amount": 10000, "winners": 1},
                    {"name": "Второй приз", "amount": 5000, "winners": 2},
                    {"name": "Третий приз", "amount": 2500, "winners": 3}
                ]
                
                winners = []
                available_users = active_users.copy()
                
                for prize in prizes:
                    if len(available_users) < prize["winners"]:
                        break
                    
                    prize_winners = random.sample(available_users, prize["winners"])
                    
                    for winner in prize_winners:
                        # Начисляем приз
                        winner.balance += prize["amount"]
                        winner.total_earned += prize["amount"]
                        
                        winners.append({
                            "user": winner,
                            "prize": prize["name"],
                            "amount": prize["amount"]
                        })
                        
                        # Убираем из доступных для следующих призов
                        available_users.remove(winner)
                
                if winners:
                    # Публикуем в канал
                    await self.channel_service.publish_lottery_results(winners)
                    
                    # Отправляем уведомления победителям
                    for winner_info in winners:
                        try:
                            message = f"🎉 Поздравляем! Вы выиграли {winner_info['prize']} в еженедельном розыгрыше!\n"
                            message += f"💰 На ваш баланс зачислено: ${winner_info['amount']:,.2f}"
                            await self.bot.send_message(winner_info['user'].telegram_id, message)
                        except Exception as e:
                            print(f"Error notifying winner {winner_info['user'].id}: {e}")
                    
                    print(f"Weekly lottery completed at {datetime.utcnow()}")
        
        except Exception as e:
            print(f"Error in weekly_lottery: {e}")
    
    async def check_events(self):
        """Проверка и публикация событий"""
        try:
            from models.transaction import Transaction
            from datetime import datetime, timedelta
            
            with db.get_session() as session:
                # Ищем крупные сделки за последний час
                hour_ago = datetime.utcnow() - timedelta(hours=1)
                large_transactions = session.query(Transaction).filter(
                    Transaction.created_at >= hour_ago,
                    Transaction.amount.abs() >= 10000
                ).all()
                
                for transaction in large_transactions:
                    await self.channel_service.publish_large_transaction(transaction)
        
        except Exception as e:
            print(f"Error in check_events: {e}")
    
    async def publish_top_players(self):
        """Публикация топ игроков в канал"""
        try:
            from services.economy_service import EconomyService
            
            economy_service = EconomyService()
            
            with db.get_session() as session:
                stats = economy_service.get_economy_stats(session)
                
                message = "🏆 ЕЖЕДНЕВНЫЙ ТОП ИГРОКОВ\n\n"
                
                for i, user in enumerate(stats['top_users'], 1):
                    message += f"{i}. @{user['username']} - ${user['balance']:,.2f}\n"
                    message += f"   Уровень: {user['level']}\n\n"
                
                await self.channel_service.publish_to_channel(message)
        
        except Exception as e:
            print(f"Error in publish_top_players: {e}")