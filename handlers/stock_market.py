from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.orm import Session # type: ignore
from database.database import db
from services.stock_service import StockService
from services.economy_service import EconomyService
from models.user import User
import datetime

router = Router()
stock_service = StockService()

class StockTrade(StatesGroup):
    choosing_stock = State()
    choosing_action = State()
    entering_quantity = State()

@router.callback_query(F.data == "stock_market")
async def show_stock_market(callback: CallbackQuery):
    """Показать фондовый рынок"""
    with db.get_session() as session:
        # Инициализируем акции, если их нет
        stock_service.init_stocks(session)
        
        stocks = stock_service.get_all_stocks(session)
        user_stocks = stock_service.get_user_stocks(session, callback.from_user.id)
        
        text = "📊 ФОНДОВЫЙ РЫНОК\n\n"
        text += "📈 Актуальные цены:\n\n"
        
        for stock in stocks[:10]:  # Показываем первые 10 акций
            change_emoji = "➡️"
            # В реальном проекте здесь было бы вычисление изменения цены
            text += f"{stock.symbol}: ${stock.current_price:,.2f} {change_emoji}\n"
        
        if len(stocks) > 10:
            text += f"\n... и еще {len(stocks) - 10} акций\n"
        
        if user_stocks:
            text += "\n🏦 ВАШИ АКЦИИ:\n"
            total_value = 0
            
            for user_stock in user_stocks[:5]:  # Показываем первые 5 позиций
                stock = stock_service.get_stock_by_symbol(session, user_stock.stock.symbol)
                if stock:
                    value = stock.current_price * user_stock.quantity
                    total_value += value
                    
                    # Расчет прибыли/убытка
                    profit_loss = (stock.current_price - user_stock.average_price) * user_stock.quantity
                    profit_percent = ((stock.current_price / user_stock.average_price) - 1) * 100
                    
                    pl_emoji = "📈" if profit_loss >= 0 else "📉"
                    pl_sign = "+" if profit_loss >= 0 else ""
                    
                    text += f"{stock.symbol}: {user_stock.quantity} шт.\n"
                    text += f"   Ср. цена: ${user_stock.average_price:,.2f}\n"
                    text += f"   Тек. цена: ${stock.current_price:,.2f}\n"
                    text += f"   {pl_emoji} {pl_sign}{profit_loss:,.2f} ({pl_sign}{profit_percent:.1f}%)\n"
            
            text += f"\n💰 Общая стоимость: ${total_value:,.2f}"
        
        # Создаем клавиатуру
        builder = InlineKeyboardBuilder()
        builder.button(text="📈 Купить акции", callback_data="buy_stock_menu")
        builder.button(text="📉 Продать акции", callback_data="sell_stock_menu")
        builder.button(text="📊 Статистика", callback_data="stock_stats")
        builder.button(text="📈 История", callback_data="stock_history_menu")
        builder.button(text="🔄 Обновить", callback_data="stock_market")
        builder.button(text="🔙 Назад", callback_data="main_menu")
        builder.adjust(2, 2, 1, 1)
        
        await callback.message.edit_text(
            text,
            reply_markup=builder.as_markup()
        )
    
    await callback.answer()

@router.callback_query(F.data == "buy_stock_menu")
async def show_buy_stock_menu(callback: CallbackQuery, state: FSMContext):
    """Меню покупки акций"""
    with db.get_session() as session:
        stocks = stock_service.get_all_stocks(session)
        user = session.query(User).filter(
            User.telegram_id == callback.from_user.id
        ).first()
        
        if not user:
            await callback.answer("Пользователь не найден")
            return
        
        text = f"📈 ПОКУПКА АКЦИЙ\n\n💰 Ваш баланс: ${user.balance:,.2f}\n\n"
        text += "Выберите акцию для покупки:\n\n"
        
        builder = InlineKeyboardBuilder()
        
        for stock in stocks[:15]:  # Ограничиваем 15 акциями
            btn_text = f"{stock.symbol} - ${stock.current_price:,.2f}"
            builder.button(text=btn_text, callback_data=f"buy_stock_{stock.symbol}")
        
        builder.button(text="🔙 Назад", callback_data="stock_market")
        builder.adjust(2)
        
        await state.set_state(StockTrade.choosing_stock)
        await callback.message.edit_text(
            text,
            reply_markup=builder.as_markup()
        )
    
    await callback.answer()

@router.callback_query(F.data.startswith("buy_stock_"))
async def choose_stock_to_buy(callback: CallbackQuery, state: FSMContext):
    """Выбор акции для покупки"""
    stock_symbol = callback.data.replace("buy_stock_", "")
    
    await state.update_data(stock_symbol=stock_symbol)
    await state.set_state(StockTrade.entering_quantity)
    
    with db.get_session() as session:
        stock = stock_service.get_stock_by_symbol(session, stock_symbol)
        user = session.query(User).filter(
            User.telegram_id == callback.from_user.id
        ).first()
        
        if not stock or not user:
            await callback.answer("Ошибка при загрузке данных")
            return
        
        max_can_buy = int(user.balance // stock.current_price)
        
        text = (
            f"📈 ПОКУПКА: {stock.symbol}\n\n"
            f"📛 Название: {stock.name}\n"
            f"💰 Текущая цена: ${stock.current_price:,.2f}\n"
            f"💼 Ваш баланс: ${user.balance:,.2f}\n"
            f"📊 Максимум можно купить: {max_can_buy} акций\n\n"
            f"Введите количество акций для покупки:"
        )
        
        builder = InlineKeyboardBuilder()
        if max_can_buy >= 1:
            builder.button(text="1 акция", callback_data=f"quick_buy_1_{stock_symbol}")
        if max_can_buy >= 10:
            builder.button(text="10 акций", callback_data=f"quick_buy_10_{stock_symbol}")
        if max_can_buy >= 100:
            builder.button(text="100 акций", callback_data=f"quick_buy_100_{stock_symbol}")
        builder.button(text="🔙 Назад", callback_data="buy_stock_menu")
        builder.adjust(3, 1)
        
        await callback.message.edit_text(
            text,
            reply_markup=builder.as_markup()
        )
    
    await callback.answer()

@router.callback_query(F.data.startswith("quick_buy_"))
async def quick_buy_stocks(callback: CallbackQuery, state: FSMContext):
    """Быстрая покупка акций"""
    data = callback.data.replace("quick_buy_", "")
    quantity_str, stock_symbol = data.split("_", 1)
    quantity = int(quantity_str)
    
    with db.get_session() as session:
        success, message = stock_service.buy_stocks(
            session, callback.from_user.id, stock_symbol, quantity
        )
        
        if success:
            stock = stock_service.get_stock_by_symbol(session, stock_symbol)
            user = session.query(User).filter(
                User.telegram_id == callback.from_user.id
            ).first()
            
            # Публикуем событие о крупной покупке
            if quantity * stock.current_price >= 10000:
                event_text = (
                    f"📈 КРУПНАЯ ПОКУПКА АКЦИЙ!\n\n"
                    f"👤 Игрок: @{callback.from_user.username or callback.from_user.first_name}\n"
                    f"🏦 Акция: {stock.symbol} ({stock.name})\n"
                    f"📊 Количество: {quantity} акций\n"
                    f"💰 Сумма: ${quantity * stock.current_price:,.2f}"
                )
                # await channel_service.publish_to_channel(event_text)
            
            text = (
                f"{message}\n\n"
                f"💰 Ваш баланс: ${user.balance:,.2f}\n\n"
                f"Хотите купить еще акций?"
            )
            
            builder = InlineKeyboardBuilder()
            builder.button(text="📈 Купить еще", callback_data="buy_stock_menu")
            builder.button(text="📊 Рынок", callback_data="stock_market")
            builder.button(text="🔙 В меню", callback_data="main_menu")
            builder.adjust(2, 1)
            
            await callback.message.edit_text(
                text,
                reply_markup=builder.as_markup()
            )
        else:
            await callback.answer(message, show_alert=True)
    
    await state.clear()
    await callback.answer()

@router.message(StockTrade.entering_quantity)
async def process_quantity_input(message: Message, state: FSMContext):
    """Обработка ввода количества акций"""
    try:
        quantity = int(message.text.strip())
        
        if quantity <= 0:
            await message.answer("Количество должно быть больше 0")
            return
        
        data = await state.get_data()
        stock_symbol = data.get('stock_symbol')
        
        if not stock_symbol:
            await message.answer("Ошибка: не выбрана акция")
            await state.clear()
            return
        
        with db.get_session() as session:
            success, msg = stock_service.buy_stocks(
                session, message.from_user.id, stock_symbol, quantity
            )
            
            if success:
                await message.answer(msg)
                
                # Показываем меню
                builder = InlineKeyboardBuilder()
                builder.button(text="📈 Купить еще", callback_data="buy_stock_menu")
                builder.button(text="📊 Рынок", callback_data="stock_market")
                builder.button(text="🔙 В меню", callback_data="main_menu")
                builder.adjust(2, 1)
                
                await message.answer(
                    "Что хотите сделать дальше?",
                    reply_markup=builder.as_markup()
                )
            else:
                await message.answer(f"❌ {msg}")
    
    except ValueError:
        await message.answer("Пожалуйста, введите число")
    
    await state.clear()

@router.callback_query(F.data == "sell_stock_menu")
async def show_sell_stock_menu(callback: CallbackQuery):
    """Меню продажи акций"""
    with db.get_session() as session:
        user_stocks = stock_service.get_user_stocks(session, callback.from_user.id)
        
        if not user_stocks:
            await callback.answer("У вас нет акций для продажи", show_alert=True)
            return
        
        text = "📉 ПРОДАЖА АКЦИЙ\n\n"
        text += "Выберите акцию для продажи:\n\n"
        
        builder = InlineKeyboardBuilder()
        
        for user_stock in user_stocks[:10]:  # Ограничиваем 10 позициями
            stock = user_stock.stock
            total_value = stock.current_price * user_stock.quantity
            
            btn_text = f"{stock.symbol} - {user_stock.quantity} шт. (${total_value:,.0f})"
            builder.button(text=btn_text, callback_data=f"sell_stock_{stock.symbol}")
        
        builder.button(text="🔙 Назад", callback_data="stock_market")
        builder.adjust(1)
        
        await callback.message.edit_text(
            text,
            reply_markup=builder.as_markup()
        )
    
    await callback.answer()

@router.callback_query(F.data.startswith("sell_stock_"))
async def choose_stock_to_sell(callback: CallbackQuery, state: FSMContext):
    """Выбор акции для продажи"""
    stock_symbol = callback.data.replace("sell_stock_", "")
    
    with db.get_session() as session:
        user_stock = stock_service.get_user_stock(session, callback.from_user.id, stock_symbol)
        
        if not user_stock:
            await callback.answer("У вас нет таких акций")
            return
        
        stock = stock_service.get_stock_by_symbol(session, stock_symbol)
        
        # Расчет потенциальной выручки
        potential_revenue = stock.current_price * user_stock.quantity
        tax = potential_revenue * 0.05  # 5% налог
        net_revenue = potential_revenue - tax
        
        # Расчет прибыли/убытка
        profit_loss = (stock.current_price - user_stock.average_price) * user_stock.quantity
        profit_percent = ((stock.current_price / user_stock.average_price) - 1) * 100
        
        pl_emoji = "📈" if profit_loss >= 0 else "📉"
        pl_sign = "+" if profit_loss >= 0 else ""
        
        text = (
            f"📉 ПРОДАЖА: {stock.symbol}\n\n"
            f"📛 Название: {stock.name}\n"
            f"💰 Текущая цена: ${stock.current_price:,.2f}\n"
            f"📊 У вас есть: {user_stock.quantity} акций\n"
            f"📈 Ср. цена покупки: ${user_stock.average_price:,.2f}\n"
            f"{pl_emoji} Прибыль/убыток: {pl_sign}{profit_loss:,.2f} ({pl_sign}{profit_percent:.1f}%)\n\n"
            f"💵 Потенциальная выручка: ${potential_revenue:,.2f}\n"
            f"🏛 Налог (5%): ${tax:,.2f}\n"
            f"💰 Чистая выручка: ${net_revenue:,.2f}\n\n"
            f"Введите количество акций для продажи:"
        )
        
        builder = InlineKeyboardBuilder()
        builder.button(text="Продать ВСЕ", callback_data=f"sell_all_{stock_symbol}")
        builder.button(text="Продать ПОЛОВИНУ", callback_data=f"sell_half_{stock_symbol}")
        builder.button(text="🔙 Назад", callback_data="sell_stock_menu")
        builder.adjust(2, 1)
        
        await state.update_data(stock_symbol=stock_symbol)
        await state.set_state(StockTrade.entering_quantity)
        
        await callback.message.edit_text(
            text,
            reply_markup=builder.as_markup()
        )
    
    await callback.answer()