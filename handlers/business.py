from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.orm import Session # type: ignore
from database.database import db
from services.business_service import BusinessService
from services.economy_service import EconomyService
from utils.keyboards import business_menu_keyboard
import json

router = Router()
business_service = BusinessService()

@router.callback_query(F.data == "businesses")
async def show_businesses(callback: CallbackQuery):
    """Показать меню бизнесов"""
    with db.get_session() as session:
        user = session.query(User).filter( # type: ignore
            User.telegram_id == callback.from_user.id # type: ignore
        ).first()
        
        if not user:
            await callback.answer("Пользователь не найден")
            return
        
        user_businesses = business_service.get_user_businesses(session, user.id)
        total_profit = business_service.calculate_total_profit_per_hour(session, user.id)
        
        text = (
            f"🏢 ВАШИ БИЗНЕСЫ\n\n"
            f"💰 Общая прибыль в час: ${total_profit:,.2f}\n"
            f"🏪 Количество бизнесов: {len(user_businesses)}\n\n"
        )
        
        if user_businesses:
            text += "📋 Ваши активные бизнесы:\n"
            for i, ub in enumerate(user_businesses[:5], 1):
                business_info = business_service.get_business_info(ub.business_type)
                if business_info:
                    text += f"{i}. {business_info['icon']} {business_info['name']} - Уровень {ub.level}\n"
                    text += f"   Прибыль/час: ${ub.profit_per_hour:,.2f}\n"
            
            if len(user_businesses) > 5:
                text += f"\n... и еще {len(user_businesses) - 5} бизнесов\n"
        else:
            text += "У вас еще нет бизнесов. Купите первый в магазине!"
        
        # Создаем клавиатуру
        builder = InlineKeyboardBuilder()
        builder.button(text="🛒 Купить бизнес", callback_data="buy_business_menu")
        builder.button(text="⬆️ Улучшить бизнес", callback_data="upgrade_business_menu")
        builder.button(text="💰 Собрать прибыль", callback_data="collect_profits")
        builder.button(text="📊 Статистика", callback_data="business_stats")
        builder.button(text="🔙 Назад", callback_data="main_menu")
        builder.adjust(2, 2, 1)
        
        await callback.message.edit_text(
            text,
            reply_markup=builder.as_markup()
        )
    
    await callback.answer()

@router.callback_query(F.data == "buy_business_menu")
async def show_buy_business_menu(callback: CallbackQuery):
    """Показать меню покупки бизнеса"""
    all_businesses = business_service.get_all_businesses()
    
    # Создаем клавиатуру с категориями
    builder = InlineKeyboardBuilder()
    
    # Получаем уникальные категории
    categories = set(b['category'] for b in all_businesses)
    
    for category in sorted(categories):
        builder.button(text=f"📁 {category.title()}", callback_data=f"category_{category}")
    
    builder.button(text="🔙 Назад", callback_data="businesses")
    builder.adjust(2)
    
    await callback.message.edit_text(
        "🏪 ВЫБОР КАТЕГОРИИ БИЗНЕСА\n\n"
        "Выберите категорию для просмотра доступных бизнесов:",
        reply_markup=builder.as_markup()
    )
    
    await callback.answer()

@router.callback_query(F.data.startswith("category_"))
async def show_businesses_in_category(callback: CallbackQuery):
    """Показать бизнесы в категории"""
    category = callback.data.replace("category_", "")
    businesses = business_service.get_businesses_by_category(category)
    
    text = f"🏪 БИЗНЕСЫ: {category.upper()}\n\n"
    
    builder = InlineKeyboardBuilder()
    
    for business in businesses[:10]:  # Ограничиваем 10 бизнесами на странице
        btn_text = f"{business['icon']} {business['name']} - ${business['base_price']:,.0f}"
        builder.button(text=btn_text, callback_data=f"view_business_{business['id']}")
    
    builder.button(text="🔙 Назад к категориям", callback_data="buy_business_menu")
    builder.adjust(1)
    
    await callback.message.edit_text(
        text,
        reply_markup=builder.as_markup()
    )
    
    await callback.answer()

@router.callback_query(F.data.startswith("view_business_"))
async def view_business_details(callback: CallbackQuery):
    """Просмотр деталей бизнеса"""
    business_id = callback.data.replace("view_business_", "")
    business_info = business_service.get_business_info(business_id)
    
    if not business_info:
        await callback.answer("Бизнес не найден")
        return
    
    with db.get_session() as session:
        user = session.query(User).filter( # type: ignore
            User.telegram_id == callback.from_user.id # type: ignore
        ).first()
        
        if not user:
            await callback.answer("Пользователь не найден")
            return
        
        # Проверяем, может ли пользователь купить этот бизнес
        can_buy, message = business_service.can_buy_business(session, user.id, business_id)
        
        text = (
            f"{business_info['icon']} {business_info['name']}\n\n"
            f"📝 {business_info['description']}\n\n"
            f"💰 Базовая цена: ${business_info['base_price']:,.2f}\n"
            f"📈 Прибыль/час (уровень 1): ${business_info['base_profit_per_hour']:,.2f}\n"
            f"⬆️ Множитель улучшения: {business_info['upgrade_multiplier']}x\n"
            f"🏆 Максимальный уровень: {business_info['max_level']}\n"
            f"📂 Категория: {business_info['category']}\n\n"
        )
        
        if can_buy:
            text += "✅ Вы можете купить этот бизнес!"
        else:
            text += f"❌ {message}"
        
        builder = InlineKeyboardBuilder()
        
        if can_buy:
            builder.button(text="✅ Купить бизнес", callback_data=f"buy_business_{business_id}")
        
        builder.button(text="📈 Показать улучшения", callback_data=f"show_upgrades_{business_id}")
        builder.button(text="🔙 Назад", callback_data=f"category_{business_info['category']}")
        builder.adjust(1)
        
        await callback.message.edit_text(
            text,
            reply_markup=builder.as_markup()
        )
    
    await callback.answer()

@router.callback_query(F.data.startswith("buy_business_"))
async def buy_business(callback: CallbackQuery):
    """Покупка бизнеса"""
    business_id = callback.data.replace("buy_business_", "")
    
    with db.get_session() as session:
        user = session.query(User).filter( # type: ignore
            User.telegram_id == callback.from_user.id # type: ignore
        ).first()
        
        if not user:
            await callback.answer("Пользователь не найден")
            return
        
        success, message, user_business = business_service.buy_business(
            session, user.id, business_id
        )
        
        if success:
            # Публикуем событие в канал
            business_info = business_service.get_business_info(business_id)
            event_text = (
                f"🎉 НОВЫЙ БИЗНЕС!\n\n"
                f"👤 Игрок: @{callback.from_user.username or callback.from_user.first_name}\n"
                f"🏪 Бизнес: {business_info['icon']} {business_info['name']}\n"
                f"💰 Стоимость: ${business_info['base_price']:,.2f}"
            )
            
            # Здесь должен быть вызов сервиса канала
            # await channel_service.publish_to_channel(event_text)
            
            # Обновляем сообщение
            text = (
                f"{message}\n\n"
                f"💰 Ваш баланс: ${user.balance:,.2f}\n"
                f"🏪 Всего бизнесов: {len(business_service.get_user_businesses(session, user.id))}\n\n"
                f"Хотите купить еще один бизнес?"
            )
            
            builder = InlineKeyboardBuilder()
            builder.button(text="🛒 Купить еще", callback_data="buy_business_menu")
            builder.button(text="🏢 Мои бизнесы", callback_data="businesses")
            builder.button(text="🔙 В меню", callback_data="main_menu")
            builder.adjust(2, 1)
            
            await callback.message.edit_text(
                text,
                reply_markup=builder.as_markup()
            )
        else:
            await callback.answer(message, show_alert=True)
    
    await callback.answer()

@router.callback_query(F.data == "collect_profits")
async def collect_profits(callback: CallbackQuery):
    """Сбор прибыли со всех бизнесов"""
    with db.get_session() as session:
        user = session.query(User).filter( # type: ignore
            User.telegram_id == callback.from_user.id # type: ignore
        ).first()
        
        if not user:
            await callback.answer("Пользователь не найден")
            return
        
        total_profit, collected_from = business_service.collect_profits(session, user.id)
        
        if total_profit > 0:
            text = f"💰 Вы собрали прибыль: ${total_profit:,.2f}\n\n"
            
            if len(collected_from) <= 5:
                text += "📊 Собрано с бизнесов:\n"
                for business_type, details in collected_from.items():
                    business_info = business_service.get_business_info(business_type)
                    if business_info:
                        text += f"{business_info['icon']} {business_info['name']} (ур. {details['level']}): ${details['profit']:,.2f}\n"
            else:
                text += f"📊 Прибыль собрана с {len(collected_from)} бизнесов\n"
            
            text += f"\n💰 Ваш баланс: ${user.balance:,.2f}"
            
            # Проверяем повышение уровня
            economy_service = EconomyService()
            leveled_up, new_level = economy_service.check_level_up(session, user.id)
            
            if leveled_up:
                text += f"\n\n🎉 ПОЗДРАВЛЯЕМ! Вы достигли уровня {new_level}!"
        else:
            text = "⏰ Прибыль еще не накопилась. Подождите хотя бы 1 час после последнего сбора."
        
        builder = InlineKeyboardBuilder()
        builder.button(text="🏢 Мои бизнесы", callback_data="businesses")
        builder.button(text="🔙 В меню", callback_data="main_menu")
        builder.adjust(1)
        
        await callback.message.edit_text(
            text,
            reply_markup=builder.as_markup()
        )
    
    await callback.answer()

@router.callback_query(F.data.startswith("show_upgrades_"))
async def show_business_upgrades(callback: CallbackQuery):
    """Показать таблицу улучшений бизнеса"""
    business_id = callback.data.replace("show_upgrades_", "")
    business_info = business_service.get_business_info(business_id)
    
    if not business_info:
        await callback.answer("Бизнес не найден")
        return
    
    text = f"📈 УЛУЧШЕНИЯ: {business_info['name']}\n\n"
    text += "Уровень | Стоимость | Прибыль/час\n"
    text += "--------|-----------|-------------\n"
    
    for level in range(1, min(6, business_info['max_level'] + 1)):  # Показываем первые 5 уровней
        upgrade_price = business_service.calculate_upgrade_price(business_info, level)
        profit = business_service.calculate_profit_per_hour(business_info, level)
        
        text += f"{level:2} | ${upgrade_price:9,.0f} | ${profit:11,.2f}\n"
    
    if business_info['max_level'] > 5:
        text += f"... и еще {business_info['max_level'] - 5} уровней\n"
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Назад", callback_data=f"view_business_{business_id}")
    
    await callback.message.edit_text(
        f"<pre>{text}</pre>",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    
    await callback.answer()