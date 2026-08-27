import datetime
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select
from models import User

router = Router()


class TransferStates(StatesGroup):
    waiting_username = State()
    waiting_amount = State()


@router.callback_query(F.data == "transfer_menu")
async def transfer_menu(callback: CallbackQuery, db):
    user = await db.get(User, callback.from_user.id)
    kb = InlineKeyboardBuilder()
    kb.button(text="💸 Отправить", callback_data="start_transfer")
    kb.button(text="🔙 Меню", callback_data="main_menu")
    kb.adjust(1)
    await callback.message.edit_text(
        f"💸 <b>Переводы</b>\n\n📊 Лимит: 🪙 {User.DAILY_TRANSFER_LIMIT:,.0f}/день\n"
        f"📊 Осталось сегодня: 🪙 {user.transfer_remaining:,.0f}\n🔥 Налог: {User.TRANSFER_TAX*100:.0f}%",
        reply_markup=kb.as_markup()
    )


@router.callback_query(F.data == "start_transfer")
async def start_transfer(callback: CallbackQuery, state: FSMContext):
    await state.set_state(TransferStates.waiting_username)
    await callback.message.answer("👤 Введи @username получателя:")
    await callback.answer()


@router.message(TransferStates.waiting_username)
async def get_recipient(message: Message, state: FSMContext, db):
    username = message.text.strip().lstrip("@")
    result = await db.execute(select(User).where(User.username == username))
    recipient = result.scalar_one_or_none()

    if not recipient:
        await message.answer("❌ Не найден. Он должен нажать /start")
        return
    if recipient.id == message.from_user.id:
        await message.answer("❌ Себе нельзя.")
        return

    await state.update_data(recipient_id=recipient.id, recipient_name=username)
    await state.set_state(TransferStates.waiting_amount)
    sender = await db.get(User, message.from_user.id)
    await message.answer(f"💰 Сумма для @{username}?\n📊 Осталось сегодня: 🪙 {sender.transfer_remaining:,.0f}")


@router.message(TransferStates.waiting_amount)
async def process_transfer(message: Message, state: FSMContext, db):
    try:
        amount = float(message.text.replace(",", "."))
    except ValueError:
        await message.answer("❌ Введи число")
        return

    data = await state.get_data()
    sender = await db.get(User, message.from_user.id)
    recipient = await db.get(User, data["recipient_id"])

    if amount < 10:
        await message.answer("❌ Минимум 10")
        return
    if amount > sender.balance:
        await message.answer(f"❌ У тебя только 🪙 {sender.balance:,.0f}")
        return
    if amount > sender.transfer_remaining:
        await message.answer(f"❌ Лимит! Осталось 🪙 {sender.transfer_remaining:,.0f}")
        return

    tax = amount * User.TRANSFER_TAX
    sender.balance -= amount
    sender.daily_transferred += amount
    sender.last_transfer_date = datetime.datetime.utcnow().date()
    recipient.balance += amount - tax
    await db.commit()
    await state.clear()

    kb = InlineKeyboardBuilder()
    kb.button(text="💸 Ещё", callback_data="start_transfer")
    kb.button(text="🔙 Меню", callback_data="main_menu")
    kb.adjust(2)
    await message.answer(
        f"✅ <b>Переведено!</b>\n👤 @{data['recipient_name']}\n"
        f"💰 🪙 {amount:,.0f} | 🔥 Налог 🪙 {tax:,.0f} | 📬 Получено 🪙 {amount-tax:,.0f}\n"
        f"📊 Остаток лимита: 🪙 {sender.transfer_remaining:,.0f}",
        reply_markup=kb.as_markup()
    )
    try:
        await message.bot.send_message(recipient.id, f"💰 Тебе перевели 🪙 {amount-tax:,.0f} от @{message.from_user.username}!")
    except Exception:
        pass