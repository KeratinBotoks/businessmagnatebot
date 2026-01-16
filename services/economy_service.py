import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session # type: ignore
from sqlalchemy import func, desc # type: ignore
from models.user import User
from models.transaction import Transaction
from config import config

class EconomyService:
    def __init__(self):
        self.levels_config = self._load_levels_config()
    
    def _load_levels_config(self) -> Dict:
        """Загрузка конфигурации уровней из JSON"""
        with open(config.LEVELS_CONFIG, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def calculate_level(self, experience: float) -> int:
        """Расчет уровня на основе опыта"""
        for level_req in reversed(self.levels_config['level_up_requirements']):
            if experience >= level_req['exp_required']:
                return level_req['level']
        return 1
    
    def get_exp_for_next_level(self, current_level: int) -> float:
        """Получение опыта до следующего уровня"""
        for i, level_req in enumerate(self.levels_config['level_up_requirements']):
            if level_req['level'] == current_level:
                if i + 1 < len(self.levels_config['level_up_requirements']):
                    next_level = self.levels_config['level_up_requirements'][i + 1]
                    return next_level['exp_required']
        return 0
    
    def get_exp_progress(self, experience: float) -> tuple[float, float, float]:
        """Получение прогресса до следующего уровня"""
        current_level = self.calculate_level(experience)
        exp_for_current = self.get_exp_for_level(current_level)
        exp_for_next = self.get_exp_for_next_level(current_level)
        
        if exp_for_next == 0:
            return 100.0, 0.0, 100.0  # Максимальный уровень
        
        exp_in_level = experience - exp_for_current
        exp_needed = exp_for_next - exp_for_current
        progress = (exp_in_level / exp_needed) * 100
        
        return round(progress, 1), exp_in_level, exp_needed
    
    def get_exp_for_level(self, level: int) -> float:
        """Получение опыта, необходимого для достижения уровня"""
        for level_req in self.levels_config['level_up_requirements']:
            if level_req['level'] == level:
                return level_req['exp_required']
        return 0
    
    def check_level_up(self, session: Session, user_id: int) -> tuple[bool, Optional[int]]:
        """Проверка повышения уровня"""
        user = session.query(User).filter(User.id == user_id).first()
        if not user:
            return False, None
        
        old_level = user.level
        new_level = self.calculate_level(user.experience)
        
        if new_level > old_level:
            user.level = new_level
            session.commit()
            return True, new_level
        
        return False, None
    
    def get_daily_bonus(self, session: Session, user_id: int) -> tuple[bool, str, float]:
        """Получение ежедневного бонуса"""
        user = session.query(User).filter(User.id == user_id).first()
        if not user:
            return False, "Пользователь не найден", 0.0
        
        now = datetime.utcnow()
        
        # Проверяем, получал ли пользователь бонус сегодня
        if user.last_daily:
            last_daily_date = user.last_daily.date()
            today = now.date()
            
            if last_daily_date == today:
                return False, "Вы уже получали бонус сегодня", 0.0
            
            # Проверяем серию дней
            yesterday = today - timedelta(days=1)
            if last_daily_date == yesterday:
                user.daily_streak += 1
            else:
                user.daily_streak = 1
        else:
            user.daily_streak = 1
        
        # Расчет бонуса
        base_bonus = config.DAILY_BONUS_BASE
        streak_multiplier = 1 + (user.daily_streak * 0.1)  # +10% за каждый день серии
        level_multiplier = 1 + (user.level * 0.05)  # +5% за каждый уровень
        
        bonus = base_bonus * streak_multiplier * level_multiplier
        bonus = round(bonus, 2)
        
        # Начисляем бонус
        user.balance += bonus
        user.total_earned += bonus
        user.last_daily = now
        
        # Создаем транзакцию
        transaction = Transaction(
            user_id=user_id,
            transaction_type='daily_bonus',
            amount=bonus,
            details={
                'streak': user.daily_streak,
                'streak_multiplier': streak_multiplier,
                'level_multiplier': level_multiplier
            }
        )
        session.add(transaction)
        
        session.commit()
        
        return True, f"🎁 Ежедневный бонус! Серия: {user.daily_streak} дней", bonus
    
    def get_economy_stats(self, session: Session) -> Dict:
        """Получение статистики экономики"""
        stats = {}
        
        # Общее количество пользователей
        stats['total_users'] = session.query(User).count()
        
        # Активные пользователи за последние 24 часа
        active_time = datetime.utcnow() - timedelta(hours=24)
        stats['active_users_24h'] = session.query(User).filter(
            User.last_daily >= active_time
        ).count()
        
        # Общий баланс всех пользователей
        total_balance_result = session.query(func.sum(User.balance)).scalar()
        stats['total_balance'] = round(total_balance_result or 0, 2)
        
        # Общий заработок
        total_earned_result = session.query(func.sum(User.total_earned)).scalar()
        stats['total_earned'] = round(total_earned_result or 0, 2)
        
        # Общие траты
        total_spent_result = session.query(func.sum(User.total_spent)).scalar()
        stats['total_spent'] = round(total_spent_result or 0, 2)
        
        # Количество транзакций за последние 24 часа
        stats['transactions_24h'] = session.query(Transaction).filter(
            Transaction.created_at >= active_time
        ).count()
        
        # Топ 5 пользователей по балансу
        top_users = session.query(User).order_by(desc(User.balance)).limit(5).all()
        stats['top_users'] = [
            {
                'username': user.username or f"User_{user.id}",
                'balance': round(user.balance, 2),
                'level': user.level
            }
            for user in top_users
        ]
        
        return stats
    
    def transfer_money(self, session: Session, from_user_id: int, to_user_id: int, amount: float) -> tuple[bool, str]:
        """Перевод денег между пользователями"""
        if amount <= 0:
            return False, "Сумма должна быть больше 0"
        
        if from_user_id == to_user_id:
            return False, "Нельзя переводить деньги самому себе"
        
        from_user = session.query(User).filter(User.id == from_user_id).first()
        to_user = session.query(User).filter(User.id == to_user_id).first()
        
        if not from_user or not to_user:
            return False, "Один из пользователей не найден"
        
        if from_user.balance < amount:
            return False, f"Недостаточно средств. Ваш баланс: ${from_user.balance:.2f}"
        
        # Комиссия за перевод
        fee = amount * 0.01  # 1% комиссия
        net_amount = amount - fee
        
        # Выполняем перевод
        from_user.balance -= amount
        to_user.balance += net_amount
        
        # Записываем транзакции
        transaction_out = Transaction(
            user_id=from_user_id,
            transaction_type='money_transfer_out',
            amount=-amount,
            details={
                'to_user_id': to_user_id,
                'to_username': to_user.username,
                'amount': amount,
                'fee': fee,
                'net_amount': net_amount
            }
        )
        
        transaction_in = Transaction(
            user_id=to_user_id,
            transaction_type='money_transfer_in',
            amount=net_amount,
            details={
                'from_user_id': from_user_id,
                'from_username': from_user.username,
                'amount': amount,
                'fee': fee,
                'net_amount': net_amount
            }
        )
        
        session.add(transaction_out)
        session.add(transaction_in)
        
        session.commit()
        
        return True, f"✅ Перевод выполнен! Получателю отправлено: ${net_amount:.2f} (комиссия: ${fee:.2f})"