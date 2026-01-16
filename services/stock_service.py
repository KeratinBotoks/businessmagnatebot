import json
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session # type: ignore
from sqlalchemy import and_ # type: ignore
from models.stock import Stock, UserStock
from models.user import User
from models.transaction import Transaction
from config import config

class StockService:
    def __init__(self):
        self.stocks_config = self._load_stocks_config()
        self.market_trend = 0.0  -0.1 до +0.1 # type: ignore
        
    def _load_stocks_config(self) -> Dict:
        """Загрузка конфигурации акций из JSON"""
        with open(config.STOCKS_CONFIG, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def init_stocks(self, session: Session):
        """Инициализация акций в базе данных"""
        existing_stocks = session.query(Stock).count()
        if existing_stocks > 0:
            return
        
        for stock_data in self.stocks_config['stocks']:
            stock = Stock(
                symbol=stock_data['symbol'],
                name=stock_data['name'],
                current_price=stock_data['base_price'],
                volatility=stock_data['volatility'],
                description=stock_data['description'],
                last_updated=datetime.utcnow()
            )
            session.add(stock)
        
        session.commit()
    
    def update_stock_prices(self, session: Session):
        """Обновление цен акций"""
        stocks = session.query(Stock).all()
        
        # Обновляем рыночный тренд
        self.market_trend += random.uniform(-0.02, 0.02)
        self.market_trend = max(-0.1, min(0.1, self.market_trend))
        
        for stock in stocks:
            # Базовое изменение цены
            change = random.uniform(-stock.volatility, stock.volatility)
            
            # Добавляем рыночный тренд
            change += self.market_trend
            
            # Добавляем небольшой рандом
            change += random.uniform(-0.05, 0.05)
            
            # Ограничиваем максимальное изменение
            change = max(-0.3, min(0.3, change))
            
            # Применяем изменение
            new_price = stock.current_price * (1 + change)
            
            # Округляем до 2 знаков
            stock.current_price = round(new_price, 2)
            stock.last_updated = datetime.utcnow()
        
        session.commit()
    
    def get_all_stocks(self, session: Session) -> List[Stock]:
        """Получение всех акций"""
        return session.query(Stock).order_by(Stock.symbol).all()
    
    def get_stock_by_symbol(self, session: Session, symbol: str) -> Optional[Stock]:
        """Получение акции по символу"""
        return session.query(Stock).filter(Stock.symbol == symbol).first()
    
    def get_user_stocks(self, session: Session, user_id: int) -> List[UserStock]:
        """Получение акций пользователя"""
        return session.query(UserStock).filter(
            UserStock.user_id == user_id
        ).join(Stock).all()
    
    def get_user_stock(self, session: Session, user_id: int, stock_symbol: str) -> Optional[UserStock]:
        """Получение конкретной акции пользователя"""
        stock = self.get_stock_by_symbol(session, stock_symbol)
        if not stock:
            return None
        
        return session.query(UserStock).filter(
            and_(
                UserStock.user_id == user_id,
                UserStock.stock_id == stock.id
            )
        ).first()
    
    def can_buy_stocks(self, session: Session, user_id: int, stock_symbol: str, quantity: int) -> tuple[bool, str, Optional[Stock]]:
        """Проверка возможности покупки акций"""
        user = session.query(User).filter(User.id == user_id).first()
        if not user:
            return False, "Пользователь не найден", None
        
        stock = self.get_stock_by_symbol(session, stock_symbol)
        if not stock:
            return False, "Акция не найдена", None
        
        if quantity <= 0:
            return False, "Количество должно быть больше 0", None
        
        total_cost = stock.current_price * quantity
        if user.balance < total_cost:
            return False, f"Недостаточно средств. Нужно: ${total_cost:.2f}", stock
        
        return True, "", stock
    
    def buy_stocks(self, session: Session, user_id: int, stock_symbol: str, quantity: int) -> tuple[bool, str]:
        """Покупка акций"""
        can_buy, message, stock = self.can_buy_stocks(session, user_id, stock_symbol, quantity)
        if not can_buy:
            return False, message
        
        user = session.query(User).filter(User.id == user_id).first()
        total_cost = stock.current_price * quantity
        
        # Вычитаем деньги
        user.balance -= total_cost
        user.total_spent += total_cost
        
        # Проверяем, есть ли уже такие акции у пользователя
        user_stock = self.get_user_stock(session, user_id, stock_symbol)
        
        if user_stock:
            # Обновляем существующие акции
            total_quantity = user_stock.quantity + quantity
            total_invested = (user_stock.average_price * user_stock.quantity) + total_cost
            user_stock.average_price = total_invested / total_quantity
            user_stock.quantity = total_quantity
        else:
            # Создаем новые акции
            user_stock = UserStock(
                user_id=user_id,
                stock_id=stock.id,
                quantity=quantity,
                average_price=stock.current_price
            )
            session.add(user_stock)
        
        # Создаем транзакцию
        transaction = Transaction(
            user_id=user_id,
            transaction_type='buy_stock',
            amount=-total_cost,
            details={
                'stock_symbol': stock_symbol,
                'stock_name': stock.name,
                'quantity': quantity,
                'price_per_share': stock.current_price,
                'total_cost': total_cost
            }
        )
        session.add(transaction)
        
        # Добавляем опыт
        user.experience += quantity * 2
        
        session.commit()
        
        return True, f"✅ Вы купили {quantity} акций {stock_symbol} за ${total_cost:.2f}"
    
    def can_sell_stocks(self, session: Session, user_id: int, stock_symbol: str, quantity: int) -> tuple[bool, str, Optional[UserStock]]:
        """Проверка возможности продажи акций"""
        user_stock = self.get_user_stock(session, user_id, stock_symbol)
        if not user_stock:
            return False, "У вас нет таких акций", None
        
        if quantity <= 0:
            return False, "Количество должно быть больше 0", None
        
        if user_stock.quantity < quantity:
            return False, f"У вас только {user_stock.quantity} акций", user_stock
        
        return True, "", user_stock
    
    def sell_stocks(self, session: Session, user_id: int, stock_symbol: str, quantity: int) -> tuple[bool, str]:
        """Продажа акций"""
        can_sell, message, user_stock = self.can_sell_stocks(session, user_id, stock_symbol, quantity)
        if not can_sell:
            return False, message
        
        stock = self.get_stock_by_symbol(session, stock_symbol)
        user = session.query(User).filter(User.id == user_id).first()
        
        total_revenue = stock.current_price * quantity
        
        # Добавляем деньги (минус налог)
        tax = total_revenue * config.TAX_RATE
        net_revenue = total_revenue - tax
        
        user.balance += net_revenue
        user.total_earned += net_revenue
        
        # Обновляем или удаляем запись об акциях
        if user_stock.quantity == quantity:
            session.delete(user_stock)
        else:
            user_stock.quantity -= quantity
        
        # Создаем транзакцию
        transaction = Transaction(
            user_id=user_id,
            transaction_type='sell_stock',
            amount=net_revenue,
            details={
                'stock_symbol': stock_symbol,
                'stock_name': stock.name,
                'quantity': quantity,
                'price_per_share': stock.current_price,
                'total_revenue': total_revenue,
                'tax': tax,
                'net_revenue': net_revenue
            }
        )
        session.add(transaction)
        
        # Добавляем опыт
        user.experience += quantity * 1
        
        session.commit()
        
        return True, f"✅ Вы продали {quantity} акций {stock_symbol} за ${net_revenue:.2f} (налог: ${tax:.2f})"
    
    def get_stock_history(self, session: Session, stock_symbol: str, days: int = 7) -> List[Dict]:
        """Получение истории цены акции (заглушка для демонстрации)"""
        stock = self.get_stock_by_symbol(session, stock_symbol)
        if not stock:
            return []
        
        # В реальном проекте здесь был бы запрос к таблице истории цен
        history = []
        base_price = stock.current_price
        
        for i in range(days):
            price = base_price * (1 + random.uniform(-0.2, 0.2))
            history.append({
                'date': (datetime.utcnow() - timedelta(days=days - i - 1)).strftime('%Y-%m-%d'),
                'price': round(price, 2)
            })
        
        return history
    
    def get_top_investors(self, session: Session, limit: int = 10) -> List[Dict]:
        """Получение топ инвесторов"""
        # Здесь должен быть сложный SQL запрос
        # Для демонстрации возвращаем заглушку
        users = session.query(User).order_by(User.balance.desc()).limit(limit).all()
        
        result = []
        for user in users:
            total_stock_value = 0
            user_stocks = self.get_user_stocks(session, user.id)
            
            for us in user_stocks:
                stock = session.query(Stock).filter(Stock.id == us.stock_id).first()
                if stock:
                    total_stock_value += stock.current_price * us.quantity
            
            result.append({
                'user': user,
                'total_stock_value': round(total_stock_value, 2)
            })
        
        return result