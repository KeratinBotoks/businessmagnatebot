from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.orm import Session # type: ignore
from database.database import db
from models.user import User
from services.economy_service import EconomyService
from utils.keyboards import main_menu_keyboard
import datetime

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    with db.get_session() as session:
        # Проверяем, есть ли пользователь в базе
        user = session.query(User).filter(
            User.telegram_id == message.from_user.id
        ).first()
        
        if not user:
            # Создаем нового пользователя
            user = User(
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                full_name=message.from_user.full_name,
                balance=1000.0,
                created_at=datetime.datetime.utcnow()
            )
            session.add(user)
            session.commit()
            
            welcome_text = (
                "🎮 Добро пожаловать в игру 'Магнат'!\n\n"
                "📊 Вы начинаете с $1,000. Ваша цель - стать самым богатым магнатом.\n\n"
                "🏪 Начните с покупки первого бизнеса в разделе 'Бизнесы'.\n"
                "📈 Инвестируйте в акции на бирже.\n"
                "🤝 Взаимодействуйте с другими игроками.\n\n"
                "🎁 Не забывайте забирать ежедневный бонус!\n\n"
                "Удачи в игре! 🚀"
            )
        else:
            welcome_text = (
                f"👋 С возвращением, {message.from_user.first_name}!\n\n"
                f"💰 Баланс: ${user.balance:,.2f}\n"
                f"📊 Уровень: {user.level}\n\n"
                "Что вы хотите сделать?"
            )
        
        # Отправляем главное меню
        await message.answer(
            welcome_text,
            reply_markup=main_menu_keyboard()
        )

@router.message(Command("profile"))
async def cmd_profile(message: Message):
    """Обработчик команды /profile"""
    with db.get_session() as session:
        user = session.query(User).filter(
            User.telegram_id == message.from_user.id
        ).first()
        
        if not user:
            await message.answer("Пользователь не найден. Используйте /start")
            return
        
        economy_service = EconomyService()
        progress, exp_current, exp_needed = economy_service.get_exp_progress(user.experience)
        
        profile_text = (
            f"👤 ПРОФИЛЬ ИГРОКА\n\n"
            f"📛 Имя: {user.full_name or 'Не указано'}\n"
            f"🔖 ID: {user.id}\n"
            f"💰 Баланс: ${user.balance:,.2f}\n"
            f"📊 Уровень: {user.level}\n"
            f"⭐ Опыт: {user.experience:,.0f}\n"
            f"📈 Прогресс: {progress}% ({exp_current:,.0f}/{exp_needed:,.0f})\n"
            f"🎁 Серия дней: {user.daily_streak}\n"
            f"📥 Всего заработано: ${user.total_earned:,.2f}\n"
            f"📤 Всего потрачено: ${user.total_spent:,.2f}\n"
            f"📅 В игре с: {user.created_at.strftime('%d.%m.%Y')}\n"
        )
        
        # Создаем клавиатуру профиля
        builder = InlineKeyboardBuilder()
        builder.button(text="🎁 Ежедневный бонус", callback_data="daily_bonus")
        builder.button(text="📊 Статистика", callback_data="stats")
        builder.button(text="🏆 Достижения", callback_data="achievements")
        builder.adjust(1)
        
        await message.answer(
            profile_text,
            reply_markup=builder.as_markup()
        )

@router.callback_query(F.data == "daily_bonus")
async def process_daily_bonus(callback: CallbackQuery):
    """Обработка ежедневного бонуса"""
    from services.economy_service import EconomyService
    
    with db.get_session() as session:
        economy_service = EconomyService()
        success, message, bonus = economy_service.get_daily_bonus(
            session, callback.from_user.id
        )
        
        if success:
            # Обновляем профиль
            user = session.query(User).filter(
                User.telegram_id == callback.from_user.id
            ).first()
            
            progress, exp_current, exp_needed = economy_service.get_exp_progress(user.experience)
            
            updated_profile = (
                f"👤 ПРОФИЛЬ ИГРОКА\n\n"
                f"📛 Имя: {user.full_name or 'Не указано'}\n"
                f"💰 Баланс: ${user.balance:,.2f}\n"
                f"📊 Уровень: {user.level}\n"
                f"⭐ Опыт: {user.experience:,.0f}\n"
                f"📈 Прогресс: {progress}% ({exp_current:,.0f}/{exp_needed:,.0f})\n"
                f"🎁 Серия дней: {user.daily_streak}\n"
            )
            
            await callback.message.edit_text(
                f"{message}\n💰 Бонус: ${bonus:,.2f}\n\n{updated_profile}"
            )
        else:
            await callback.answer(message, show_alert=True)
    
    await callback.answer()

@router.callback_query(F.data == "main_menu")
async def process_main_menu(callback: CallbackQuery):
    """Возврат в главное меню"""
    await callback.message.edit_text(
        "🎮 Главное меню игры 'Магнат'\n\nВыберите раздел:",
        reply_markup=main_menu_keyboard()
    )