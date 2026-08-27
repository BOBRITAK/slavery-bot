from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router()


def main_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="👤 Мои рабы", callback_data="my_slaves")
    kb.button(text="🛒 Рынок", callback_data="market")
    kb.button(text="🏪 Новички", callback_data="newcomer_market")
    kb.button(text="💼 Работа", callback_data="work")
    kb.button(text="💸 Перевод", callback_data="transfer_menu")
    kb.button(text="📊 Рейтинг", callback_data="top")
    kb.adjust(2)
    return kb.as_markup()


@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "⛓️ <b>Рабство 2.0</b>\n\n"
        "Покупай рабов, прокачивай, зарабатывай!\n"
        "🏪 Рынок новичков — для тех кто начинает.",
        reply_markup=main_keyboard()
    )


@router.callback_query(F.data == "main_menu")
async def back_to_menu(callback: CallbackQuery):
    await callback.message.edit_text("⛓️ <b>Рабство 2.0</b>", reply_markup=main_keyboard())