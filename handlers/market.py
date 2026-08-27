from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select, and_
from models import Slave, User, RARITY_NAMES
from services.economy import calc_tax

router = Router()


@router.callback_query(F.data == "market")
async def show_market(callback: CallbackQuery, db):
    result = await db.execute(
        select(Slave).where(and_(Slave.newcomer_market == False, Slave.owner_id != callback.from_user.id))
        .order_by(Slave.market_price.asc()).limit(10)
    )
    slaves = result.scalars().all()

    if not slaves:
        kb = InlineKeyboardBuilder()
        kb.button(text="🏪 Новички", callback_data="newcomer_market")
        kb.button(text="🔙 Меню", callback_data="main_menu")
        kb.adjust(2)
        await callback.message.edit_text("🛒 <b>Рынок пуст</b>", reply_markup=kb.as_markup())
        return

    text = "🛒 <b>Рынок рабов</b>\n\n"
    kb = InlineKeyboardBuilder()
    for s in slaves:
        cls_name, _ = s.slave_class
        target_name = s.target.username if s.target else str(s.target_id)
        price = s.market_price
        text += (
            f"{'─' * 25}\n👤 @{target_name}\n"
            f"📊 Ур. {s.level} | {cls_name} | {RARITY_NAMES[s.rarity]}\n"
            f"💵 🪙 {s.income_per_hour:,.2f}/час | 💲 🪙 {price:,.0f}\n"
        )
        kb.button(text=f"🛒 @{target_name} 🪙{price:,.0f}", callback_data=f"buy_{s.id}")

    kb.button(text="🔙 Меню", callback_data="main_menu")
    kb.adjust(1)
    await callback.message.edit_text(text, reply_markup=kb.as_markup())


@router.callback_query(F.data.startswith("buy_"))
async def buy_slave(callback: CallbackQuery, db):
    slave_id = int(callback.data.split("_")[1])
    slave = await db.get(Slave, slave_id)

    if not slave or slave.newcomer_market:
        await callback.answer("Уже продан", show_alert=True)
        return

    user = await db.get(User, callback.from_user.id)
    price = slave.market_price
    tax = calc_tax(price)

    if user.balance < price:
        await callback.answer(f"❌ Нужно 🪙 {price:,.0f}", show_alert=True)
        return

    seller = await db.get(User, slave.owner_id)
    user.balance -= price
    seller.balance += price - tax
    slave.owner_id = callback.from_user.id
    slave.last_bought_at = None
    await db.commit()

    cls_name, _ = slave.slave_class
    target_name = slave.target.username if slave.target else str(slave.target_id)

    kb = InlineKeyboardBuilder()
    kb.button(text="👤 Мои рабы", callback_data="my_slaves")
    kb.button(text="🛒 Ещё", callback_data="market")
    kb.button(text="🔙 Меню", callback_data="main_menu")
    kb.adjust(2)
    await callback.message.edit_text(
        f"✅ <b>Куплен!</b>\n👤 @{target_name}\n📊 {cls_name} | Ур. {slave.level}\n"
        f"💵 🪙 {slave.income_per_hour:,.2f}/час\n💸 🪙 {price:,.0f} | 🔥 Налог 🪙 {tax:,.0f}",
        reply_markup=kb.as_markup()
    )
    await callback.answer("✅ Куплено!")