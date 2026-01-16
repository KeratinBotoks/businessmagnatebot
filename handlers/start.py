from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    welcome_text = (
        "🎮 Добро пожаловать в игру 'Магнат'!\n\n"
        "📊 Вы начинаете с $1,000. Ваша цель - стать самым богатым магнатом.\n\n"
        "🏪 Начните с покупки первого бизнеса\n"
        "📈 Инвестируйте в акции на бирже\n"
        "🤝 Взаимодействуйте с другими игроками\n\n"
        "🎁 Не забывайте забирать ежедневный бонус!\n\n"
        "Удачи в игре! 🚀"
    )
    
    # Создаем клавиатуру главного меню
    builder = InlineKeyboardBuilder()
    builder.button(text="👤 Профиль", callback_data="profile")
    builder.button(text="🏢 Бизнесы", callback_data="businesses")
    builder.button(text="📊 Биржа", callback_data="stock_market")
    builder.button(text="🤝 Игроки", callback_data="players")
    builder.button(text="❓ Помощь", callback_data="help")
    builder.adjust(2, 2, 1)
    
    await message.answer(welcome_text, reply_markup=builder.as_markup())