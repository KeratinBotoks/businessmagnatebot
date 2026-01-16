from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.orm import Session # type: ignore
from database.database import db
from models.user import User
from services.economy_service import EconomyService
from services.stock_service import StockService
from config import config
import json

router = Router()

class AdminBroadcast(StatesGroup):
    entering_message = State()

def is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь администратором"""
    return user_id in config.ADMIN_IDS

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    """Команда админ-панели"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав администратора")
        return
    
    text = (
        "⚙️ АДМИН-ПАНЕЛЬ\n\n"
        "Доступные команды:\n\n"
        "📊 /stats - статистика игры\n"
        "👥 /users - управление пользователями\n"
        "📢 /broadcast - рассылка сообщений\n"
        "🎰 /lottery - запуск розыгрыша\n"
        "📈 /stocks - управление акциями\n"
        "💰 /economy - управление экономикой\n"
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Статистика", callback_data="admin_stats")
    builder.button(text="👥 Пользователи", callback_data="admin_users")
    builder.button(text="📢 Рассылка", callback_data="admin_broadcast")
    builder.button(text="🎰 Розыгрыш", callback_data="admin_lottery")
    builder.adjust(2, 2)
    
    await message.answer(
        text,
        reply_markup=builder.as_markup()
    )

@router.message(Command("stats"))
async def cmd_stats(message: Message):
    """Статистика игры"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав администратора")
        return
    
    economy_service = EconomyService()
    
    with db.get_session() as session:
        stats = economy_service.get_economy_stats(session)
        
        text = (
            "📊 СТАТИСТИКА ИГРЫ\n\n"
            f"👥 Всего пользователей: {stats['total_users']}\n"
            f"🎯 Активных за 24ч: {stats['active_users_24h']}\n"
            f"💰 Общий баланс: ${stats['total_balance']:,.2f}\n"
            f"📈 Всего заработано: ${stats['total_earned']:,.2f}\n"
            f"📉 Всего потрачено: ${stats['total_spent']:,.2f}\n"
            f"🔄 Транзакций за 24ч: {stats['transactions_24h']}\n\n"
            "🏆 ТОП-5 ИГРОКОВ:\n"
        )
        
        for i, user in enumerate(stats['top_users'], 1):
            text += f"{i}. @{user['username']} - ${user['balance']:,.2f} (ур. {user['level']})\n"
        
        await message.answer(text)

@router.callback_query(F.data == "admin_stats")
async def admin_stats_callback(callback: CallbackQuery):
    """Статистика через callback"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ У вас нет прав администратора")
        return
    
    await cmd_stats(callback.message)
    await callback.answer()

@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, state: FSMContext):
    """Рассылка сообщений"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав администратора")
        return
    
    await state.set_state(AdminBroadcast.entering_message)
    await message.answer(
        "📢 РАССЫЛКА СООБЩЕНИЙ\n\n"
        "Введите сообщение для рассылки всем пользователям:"
    )

@router.message(AdminBroadcast.entering_message)
async def process_broadcast_message(message: Message, state: FSMContext):
    """Обработка сообщения для рассылки"""
    broadcast_text = message.text
    
    with db.get_session() as session:
        users = session.query(User).filter(User.is_banned == False).all()
        
        success_count = 0
        fail_count = 0
        
        # Отправляем сообщение автору
        await message.answer(f"🔄 Начинаю рассылку сообщения для {len(users)} пользователей...")
        
        for user in users:
            try:
                await message.bot.send_message(
                    user.telegram_id,
                    f"📢 ОБЪЯВЛЕНИЕ ОТ АДМИНИСТРАЦИИ:\n\n{broadcast_text}"
                )
                success_count += 1
            except Exception as e:
                print(f"Failed to send to user {user.id}: {e}")
                fail_count += 1
        
        await message.answer(
            f"✅ Рассылка завершена!\n\n"
            f"✅ Успешно: {success_count}\n"
            f"❌ Не удалось: {fail_count}"
        )
    
    await state.clear()

@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_callback(callback: CallbackQuery, state: FSMContext):
    """Рассылка через callback"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ У вас нет прав администратора")
        return
    
    await cmd_broadcast(callback.message, state)
    await callback.answer()

@router.message(Command("lottery"))
async def cmd_lottery(message: Message):
    """Запуск розыгрыша вручную"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав администратора")
        return
    
    from services.scheduler_service import SchedulerService
    
    await message.answer("🎰 Запуск еженедельного розыгрыша...")
    
    # Здесь нужно получить экземпляр бота, в реальном проекте это делается иначе
    # Для демонстрации просто отправляем сообщение
    await message.answer("Розыгрыш будет проведен автоматически в воскресенье в 20:00")

@router.message(Command("users"))
async def cmd_users(message: Message):
    """Управление пользователями"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав администратора")
        return
    
    with db.get_session() as session:
        total_users = session.query(User).count()
        active_users = session.query(User).filter(
            User.last_daily >= datetime.utcnow() - timedelta(days=1) # type: ignore
        ).count()
        banned_users = session.query(User).filter(User.is_banned == True).count()
        
        text = (
            "👥 УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ\n\n"
            f"📊 Всего пользователей: {total_users}\n"
            f"🎯 Активных за 24ч: {active_users}\n"
            f"⛔ Заблокированных: {banned_users}\n\n"
            "Доступные действия:"
        )
        
        builder = InlineKeyboardBuilder()
        builder.button(text="🔍 Поиск пользователя", callback_data="admin_find_user")
        builder.button(text="📊 Топ пользователей", callback_data="admin_top_users")
        builder.button(text="⛔ Блокировки", callback_data="admin_bans")
        builder.button(text="🔙 Назад", callback_data="admin_menu")
        builder.adjust(2, 2)
        
        await message.answer(
            text,
            reply_markup=builder.as_markup()
        )

@router.callback_query(F.data == "admin_menu")
async def admin_menu_callback(callback: CallbackQuery):
    """Возврат в админ-меню"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ У вас нет прав администратора")
        return
    
    await cmd_admin(callback.message)
    await callback.answer()