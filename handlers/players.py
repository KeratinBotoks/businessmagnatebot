from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.orm import Session # type: ignore
from database.database import db
from models.user import User
from services.economy_service import EconomyService
import random

router = Router()

class MoneyTransfer(StatesGroup):
    entering_username = State()
    entering_amount = State()

@router.callback_query(F.data == "players")
async def show_players_menu(callback: CallbackQuery):
    """Меню взаимодействия с игроками"""
    text = (
        "🤝 ВЗАИМОДЕЙСТВИЕ С ИГРОКАМИ\n\n"
        "Выберите действие:\n\n"
        "💰 Перевод денег - отправить деньги другому игроку\n"
        "📊 Рейтинг - топ игроков по балансу\n"
        "🔍 Найти игрока - поиск по имени или username\n"
        "🏢 Рынок труда - найм других игроков\n"
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="💰 Перевод денег", callback_data="transfer_money")
    builder.button(text="📊 Рейтинг игроков", callback_data="player_rating")
    builder.button(text="🔍 Найти игрока", callback_data="find_player")
    builder.button(text="🏢 Рынок труда", callback_data="job_market")
    builder.button(text="🔙 Назад", callback_data="main_menu")
    builder.adjust(2, 2, 1)
    
    await callback.message.edit_text(
        text,
        reply_markup=builder.as_markup()
    )
    
    await callback.answer()

@router.callback_query(F.data == "transfer_money")
async def start_transfer_money(callback: CallbackQuery, state: FSMContext):
    """Начало перевода денег"""
    with db.get_session() as session:
        user = session.query(User).filter(
            User.telegram_id == callback.from_user.id
        ).first()
        
        text = (
            f"💰 ПЕРЕВОД ДЕНЕГ\n\n"
            f"Ваш баланс: ${user.balance:,.2f}\n\n"
            f"Введите username получателя (например, @username или просто username):"
        )
        
        builder = InlineKeyboardBuilder()
        builder.button(text="🔙 Назад", callback_data="players")
        
        await state.set_state(MoneyTransfer.entering_username)
        await callback.message.edit_text(
            text,
            reply_markup=builder.as_markup()
        )
    
    await callback.answer()

@router.message(MoneyTransfer.entering_username)
async def process_username_input(message: Message, state: FSMContext):
    """Обработка ввода username"""
    username = message.text.strip().lstrip('@')
    
    if not username:
        await message.answer("Пожалуйста, введите username")
        return
    
    with db.get_session() as session:
        # Ищем пользователя по username
        recipient = session.query(User).filter(
            User.username.ilike(f"%{username}%")
        ).first()
        
        if not recipient:
            await message.answer(f"Игрок с username '{username}' не найден")
            return
        
        if recipient.telegram_id == message.from_user.id:
            await message.answer("Нельзя переводить деньги самому себе")
            return
        
        await state.update_data(recipient_id=recipient.id)
        await state.set_state(MoneyTransfer.entering_amount)
        
        sender = session.query(User).filter(
            User.telegram_id == message.from_user.id
        ).first()
        
        text = (
            f"💰 ПЕРЕВОД ДЕНЕГ\n\n"
            f"Отправитель: {sender.full_name or sender.username}\n"
            f"Получатель: {recipient.full_name or recipient.username}\n"
            f"Ваш баланс: ${sender.balance:,.2f}\n\n"
            f"Введите сумму для перевода:"
        )
        
        await message.answer(text)

@router.message(MoneyTransfer.entering_amount)
async def process_amount_input(message: Message, state: FSMContext):
    """Обработка ввода суммы перевода"""
    try:
        amount = float(message.text.strip())
        
        if amount <= 0:
            await message.answer("Сумма должна быть больше 0")
            return
        
        data = await state.get_data()
        recipient_id = data.get('recipient_id')
        
        if not recipient_id:
            await message.answer("Ошибка: получатель не найден")
            await state.clear()
            return
        
        with db.get_session() as session:
            economy_service = EconomyService()
            sender = session.query(User).filter(
                User.telegram_id == message.from_user.id
            ).first()
            
            success, message_text = economy_service.transfer_money(
                session, sender.id, recipient_id, amount
            )
            
            if success:
                # Обновляем информацию об отправителе
                sender = session.query(User).filter(
                    User.telegram_id == message.from_user.id
                ).first()
                
                # Получаем информацию о получателе
                recipient = session.query(User).filter(
                    User.id == recipient_id
                ).first()
                
                text = (
                    f"{message_text}\n\n"
                    f"💰 Ваш баланс: ${sender.balance:,.2f}\n"
                    f"👤 Получатель: {recipient.full_name or recipient.username}\n\n"
                    f"Хотите сделать еще один перевод?"
                )
                
                builder = InlineKeyboardBuilder()
                builder.button(text="💰 Еще перевод", callback_data="transfer_money")
                builder.button(text="🤝 К игрокам", callback_data="players")
                builder.button(text="🔙 В меню", callback_data="main_menu")
                builder.adjust(2, 1)
                
                await message.answer(
                    text,
                    reply_markup=builder.as_markup()
                )
            else:
                await message.answer(f"❌ {message_text}")
    
    except ValueError:
        await message.answer("Пожалуйста, введите число")
    
    await state.clear()

@router.callback_query(F.data == "player_rating")
async def show_player_rating(callback: CallbackQuery):
    """Показать рейтинг игроков"""
    with db.get_session() as session:
        # Топ-20 игроков по балансу
        top_players = session.query(User).filter(
            User.is_banned == False
        ).order_by(
            User.balance.desc()
        ).limit(20).all()
        
        text = "🏆 РЕЙТИНГ ИГРОКОВ (по балансу)\n\n"
        
        for i, player in enumerate(top_players, 1):
            medal = ""
            if i == 1:
                medal = "🥇"
            elif i == 2:
                medal = "🥈"
            elif i == 3:
                medal = "🥉"
            
            username = player.username or player.full_name or f"Игрок_{player.id}"
            text += f"{medal} {i}. @{username}\n"
            text += f"   💰 ${player.balance:,.2f} | 📊 Ур. {player.level}\n\n"
        
        builder = InlineKeyboardBuilder()
        builder.button(text="🔄 Обновить", callback_data="player_rating")
        builder.button(text="🔙 Назад", callback_data="players")
        
        await callback.message.edit_text(
            text,
            reply_markup=builder.as_markup()
        )
    
    await callback.answer()

@router.callback_query(F.data == "job_market")
async def show_job_market(callback: CallbackQuery):
    """Показать рынок труда"""
    text = (
        "🏢 РЫНОК ТРУДА\n\n"
        "Здесь вы можете:\n\n"
        "👨‍💼 Нанять работника - наймите другого игрока для работы в вашем бизнесе\n"
        "👨‍💻 Найти работу - станьте работником у другого игрока\n"
        "📋 Мои предложения - просмотр ваших предложений работы\n"
        "🤝 Активные контракты - ваши текущие рабочие отношения\n\n"
        "⚡ Функция в разработке..."
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="👨‍💼 Нанять работника", callback_data="hire_worker")
    builder.button(text="👨‍💻 Найти работу", callback_data="find_job")
    builder.button(text="🔙 Назад", callback_data="players")
    
    await callback.message.edit_text(
        text,
        reply_markup=builder.as_markup()
    )
    
    await callback.answer()