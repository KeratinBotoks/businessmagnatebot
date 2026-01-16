from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import InlineKeyboardButton, KeyboardButton

def main_menu_keyboard():
    """Клавиатура главного меню"""
    builder = InlineKeyboardBuilder()
    
    builder.button(text="👤 Профиль", callback_data="profile")
    builder.button(text="🏢 Бизнесы", callback_data="businesses")
    builder.button(text="📊 Биржа", callback_data="stock_market")
    builder.button(text="🤝 Игроки", callback_data="players")
    builder.button(text="🎮 Игры", callback_data="games")
    builder.button(text="🏆 Топы", callback_data="leaderboards")
    builder.button(text="⚙️ Настройки", callback_data="settings")
    builder.button(text="❓ Помощь", callback_data="help")
    
    builder.adjust(2, 2, 2, 2)
    return builder.as_markup()

def business_menu_keyboard():
    """Клавиатура меню бизнесов"""
    builder = InlineKeyboardBuilder()
    
    builder.button(text="🛒 Купить бизнес", callback_data="buy_business_menu")
    builder.button(text="⬆️ Улучшить бизнес", callback_data="upgrade_business_menu")
    builder.button(text="💰 Собрать прибыль", callback_data="collect_profits")
    builder.button(text="📊 Мои бизнесы", callback_data="my_businesses")
    builder.button(text="📈 Статистика", callback_data="business_stats")
    builder.button(text="🔙 Назад", callback_data="main_menu")
    
    builder.adjust(2, 2, 1, 1)
    return builder.as_markup()

def stock_market_keyboard():
    """Клавиатура фондового рынка"""
    builder = InlineKeyboardBuilder()
    
    builder.button(text="📈 Купить", callback_data="buy_stock_menu")
    builder.button(text="📉 Продать", callback_data="sell_stock_menu")
    builder.button(text="📊 Портфель", callback_data="stock_portfolio")
    builder.button(text="📈 Топ акций", callback_data="top_stocks")
    builder.button(text="📉 История", callback_data="stock_history")
    builder.button(text="🔄 Обновить", callback_data="stock_market")
    builder.button(text="🔙 Назад", callback_data="main_menu")
    
    builder.adjust(2, 2, 2, 1)
    return builder.as_markup()

def back_to_main_keyboard():
    """Клавиатура с кнопкой назад в главное меню"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 В главное меню", callback_data="main_menu")
    return builder.as_markup()