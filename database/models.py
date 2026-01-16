from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, JSON, ForeignKey, Text # type: ignore
from sqlalchemy.ext.declarative import declarative_base # type: ignore
from sqlalchemy.orm import sessionmaker, relationship # type: ignore
from datetime import datetime
import json

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    username = Column(String(100))
    full_name = Column(String(200))
    balance = Column(Float, default=1000.0)
    level = Column(Integer, default=1)
    experience = Column(Float, default=0.0)
    daily_streak = Column(Integer, default=0)
    last_daily = Column(DateTime)
    total_earned = Column(Float, default=0.0)
    total_spent = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_banned = Column(Boolean, default=False)
    
    businesses = relationship("UserBusiness", back_populates="user")
    stocks = relationship("UserStock", back_populates="user")
    transactions = relationship("Transaction", back_populates="user")

class UserBusiness(Base):
    __tablename__ = 'user_businesses'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    business_type = Column(String(50), nullable=False)
    level = Column(Integer, default=1)
    profit_per_hour = Column(Float, default=0.0)
    last_collected = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="businesses")

class Stock(Base):
    __tablename__ = 'stocks'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    current_price = Column(Float, default=100.0)
    volatility = Column(Float, default=0.1)
    last_updated = Column(DateTime, default=datetime.utcnow)
    description = Column(Text)

class UserStock(Base):
    __tablename__ = 'user_stocks'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    stock_id = Column(Integer, ForeignKey('stocks.id'), nullable=False, index=True)
    quantity = Column(Integer, default=0)
    average_price = Column(Float, default=0.0)
    
    user = relationship("User", back_populates="stocks")
    stock = relationship("Stock")

class Transaction(Base):
    __tablename__ = 'transactions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    transaction_type = Column(String(50), nullable=False)  # buy_business, upgrade, stock_buy, stock_sell, etc.
    amount = Column(Float, nullable=False)
    details = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="transactions")

class Achievement(Base):
    __tablename__ = 'achievements'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    achievement_type = Column(String(50), nullable=False)
    achieved_at = Column(DateTime, default=datetime.utcnow)
    details = Column(JSON)

class JobOffer(Base):
    __tablename__ = 'job_offers'
    
    id = Column(Integer, primary_key=True)
    employer_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    employee_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    salary = Column(Float, nullable=False)
    duration_hours = Column(Integer, default=24)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), default='open')  # open, accepted, completed, expired
    
    employer = relationship("User", foreign_keys=[employer_id])
    employee = relationship("User", foreign_keys=[employee_id])