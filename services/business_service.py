import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session # type: ignore
from models.user import User, UserBusiness
from models.transaction import Transaction
from config import config
import math

class BusinessService:
    def __init__(self):
        self.businesses_config = self._load_businesses_config()
    
    def _load_businesses_config(self) -> Dict:
        """Загрузка конфигурации бизнесов из JSON"""
        with open(config.BUSINESSES_CONFIG, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def get_business_info(self, business_id: str) -> Optional[Dict]:
        """Получение информации о бизнесе"""
        for business in self.businesses_config['businesses']:
            if business['id'] == business_id:
                return business
        return None
    
    def get_all_businesses(self) -> List[Dict]:
        """Получение списка всех бизнесов"""
        return self.businesses_config['businesses']
    
    def get_businesses_by_category(self, category: str) -> List[Dict]:
        """Получение бизнесов по категории"""
        return [b for b in self.businesses_config['businesses'] if b.get('category') == category]
    
    def calculate_upgrade_price(self, business_info: Dict, current_level: int) -> float:
        """Расчет стоимости улучшения бизнеса"""
        base_price = business_info['base_price']
        multiplier = business_info['upgrade_multiplier']
        
        # Нелинейный рост цены
        price = base_price * (multiplier ** (current_level - 1))
        return round(price, 2)
    
    def calculate_profit_per_hour(self, business_info: Dict, level: int) -> float:
        """Расчет прибыли в час для уровня"""
        base_profit = business_info['base_profit_per_hour']
        multiplier = business_info['upgrade_multiplier']
        
        profit = base_profit * (multiplier ** (level - 1))
        return round(profit, 2)
    
    def can_buy_business(self, session: Session, user_id: int, business_id: str) -> tuple[bool, str]:
        """Проверка, может ли пользователь купить бизнес"""
        user = session.query(User).filter(User.id == user_id).first()
        if not user:
            return False, "Пользователь не найден"
        
        business_info = self.get_business_info(business_id)
        if not business_info:
            return False, "Бизнес не найден"
        
        # Проверка уровня
        user_business_count = session.query(UserBusiness).filter(
            UserBusiness.user_id == user_id
        ).count()
        
        # Проверка максимального количества бизнесов для уровня
        max_businesses = self._get_max_businesses_for_level(user.level)
        if user_business_count >= max_businesses:
            return False, f"Достигнут лимит бизнесов для вашего уровня ({max_businesses})"
        
        # Проверка баланса
        price = business_info['base_price']
        if user.balance < price:
            return False, f"Недостаточно средств. Нужно: ${price:.2f}"
        
        return True, ""
    
    def buy_business(self, session: Session, user_id: int, business_id: str) -> tuple[bool, str, Optional[UserBusiness]]:
        """Покупка бизнеса"""
        can_buy, message = self.can_buy_business(session, user_id, business_id)
        if not can_buy:
            return False, message, None
        
        user = session.query(User).filter(User.id == user_id).first()
        business_info = self.get_business_info(business_id)
        
        # Вычитаем деньги
        price = business_info['base_price']
        user.balance -= price
        user.total_spent += price
        
        # Создаем запись о бизнесе
        user_business = UserBusiness(
            user_id=user_id,
            business_type=business_id,
            level=1,
            profit_per_hour=self.calculate_profit_per_hour(business_info, 1),
            last_collected=datetime.utcnow()
        )
        session.add(user_business)
        
        # Создаем транзакцию
        transaction = Transaction(
            user_id=user_id,
            transaction_type='buy_business',
            amount=-price,
            details={
                'business_type': business_id,
                'business_name': business_info['name'],
                'level': 1
            }
        )
        session.add(transaction)
        
        # Добавляем опыт
        user.experience += 50  # Из конфига levels.json
        
        session.commit()
        
        return True, f"✅ Вы успешно купили {business_info['icon']} {business_info['name']}!", user_business
    
    def can_upgrade_business(self, session: Session, user_id: int, business_id: int) -> tuple[bool, str, Optional[Dict]]:
        """Проверка возможности улучшения бизнеса"""
        user_business = session.query(UserBusiness).filter(
            UserBusiness.id == business_id,
            UserBusiness.user_id == user_id
        ).first()
        
        if not user_business:
            return False, "Бизнес не найден", None
        
        business_info = self.get_business_info(user_business.business_type)
        if not business_info:
            return False, "Информация о бизнесе не найдена", None
        
        if user_business.level >= business_info['max_level']:
            return False, f"Бизнес достиг максимального уровня ({business_info['max_level']})", None
        
        user = session.query(User).filter(User.id == user_id).first()
        upgrade_price = self.calculate_upgrade_price(business_info, user_business.level)
        
        if user.balance < upgrade_price:
            return False, f"Недостаточно средств. Нужно: ${upgrade_price:.2f}", None
        
        return True, "", business_info
    
    def upgrade_business(self, session: Session, user_id: int, business_id: int) -> tuple[bool, str]:
        """Улучшение бизнеса"""
        can_upgrade, message, business_info = self.can_upgrade_business(session, user_id, business_id)
        if not can_upgrade:
            return False, message
        
        user_business = session.query(UserBusiness).filter(
            UserBusiness.id == business_id,
            UserBusiness.user_id == user_id
        ).first()
        
        user = session.query(User).filter(User.id == user_id).first()
        upgrade_price = self.calculate_upgrade_price(business_info, user_business.level)
        
        # Вычитаем деньги
        user.balance -= upgrade_price
        user.total_spent += upgrade_price
        
        # Улучшаем бизнес
        user_business.level += 1
        user_business.profit_per_hour = self.calculate_profit_per_hour(business_info, user_business.level)
        
        # Создаем транзакцию
        transaction = Transaction(
            user_id=user_id,
            transaction_type='upgrade_business',
            amount=-upgrade_price,
            details={
                'business_type': user_business.business_type,
                'business_name': business_info['name'],
                'old_level': user_business.level - 1,
                'new_level': user_business.level
            }
        )
        session.add(transaction)
        
        # Добавляем опыт
        user.experience += 25  # Из конфига levels.json
        
        session.commit()
        
        return True, f"✅ Бизнес {business_info['icon']} {business_info['name']} улучшен до уровня {user_business.level}!"
    
    def collect_profits(self, session: Session, user_id: int) -> tuple[float, Dict]:
        """Сбор прибыли со всех бизнесов пользователя"""
        user_businesses = session.query(UserBusiness).filter(
            UserBusiness.user_id == user_id
        ).all()
        
        total_profit = 0.0
        collected_from = {}
        
        for ub in user_businesses:
            hours_passed = (datetime.utcnow() - ub.last_collected).total_seconds() / 3600
            
            if hours_passed >= 1:  # Собираем минимум за 1 час
                profit = ub.profit_per_hour * hours_passed
                total_profit += profit
                
                collected_from[ub.business_type] = {
                    'profit': profit,
                    'hours': hours_passed,
                    'level': ub.level
                }
                
                ub.last_collected = datetime.utcnow()
        
        if total_profit > 0:
            user = session.query(User).filter(User.id == user_id).first()
            user.balance += total_profit
            user.total_earned += total_profit
            
            # Добавляем опыт за сбор прибыли
            user.experience += total_profit * 0.1  # 10% от прибыли в опыт
            
            session.commit()
        
        return round(total_profit, 2), collected_from
    
    def get_user_businesses(self, session: Session, user_id: int) -> List[UserBusiness]:
        """Получение всех бизнесов пользователя"""
        return session.query(UserBusiness).filter(
            UserBusiness.user_id == user_id
        ).all()
    
    def calculate_total_profit_per_hour(self, session: Session, user_id: int) -> float:
        """Расчет общей прибыли в час"""
        user_businesses = self.get_user_businesses(session, user_id)
        total = sum(ub.profit_per_hour for ub in user_businesses)
        return round(total, 2)
    
    def _get_max_businesses_for_level(self, level: int) -> int:
        """Получение максимального количества бизнесов для уровня"""
        with open(config.LEVELS_CONFIG, 'r', encoding='utf-8') as f:
            levels_config = json.load(f)
        
        for req in levels_config['level_up_requirements']:
            if req['level'] == level:
                return req['business_limit']
        
        return 1