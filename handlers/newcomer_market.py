from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select, and_
from models import Slave, User, RARITY_NAMES
from services.economy import calc_tax

router = Router()


def is_newcomer_buyer(user: User) -> tuple[bool, str]:
    if user.balance < Slave.NEWCOMER_BUYER_MAX_BALANCE:
        return True, ""
    account_age = (datetime.utcnow() - user.created_at).days
    if account_age < Slave.NEWCOMER_BUYER_MAX_AGE_DAYS:
        return True, ""
    return False, (
        f"❌ Ты слишком богатый для рынка новичков!\n"
        f"📊 Баланс: 🪙 {user.balance:,.0f} (лимит 🪙 {Slave.NEWCOMER_BUYER_MAX_BALANCE:,.0f})\n"
        f"Иди на обычный рынок 🛒"
    )


def can_list_on_newcomer(slave: Slave) -> tuple[bool, str]:
    if slave.level > Slave.NEWCOMER_MAX_LEVEL:
        return False, f"❌ Макс. уровень: {Slave.NEWCOMER_MAX_LEVEL}"
    price = slave.market_price
    if price > Slave.NEWCOMER_MAX_PRICE:
        return False, f"❌ Цена 🪙 {price:,.0f} > лимит 🪙 {Slave.NEWCOMER_MAX_PRICE:,.0f}"
    if slave.last_bought_at:
        cooldown_end = slave.last_bought_at + timedelta(hours=Slave.NEWCOMER_COOLDOWN_HOURS)
        if datetime.utcnow() < cooldown_end:
            hours = int((cooldown_end - datetime.utcnow()).total_seconds() // 3600)
            return False, f"⏳ Кулдаун ещё {hours}ч"
    return True, ""


@router.callback_query(F.data == "newcomer_market")
async def newcomer_market(callback: CallbackQuery, db):
    user = await db.get(User, callback.from_user.id)
    allowed, reason = is_newcomer_buyer(user)
    if not allowed:
        await callback.answer(reason, show_alert=True)
        return

    result = await db.execute(
        select(Slave).where(
            and_(Slave.newcomer_market == True, Slave.level <= Slave.NEWCOMER_MAX_LEVEL)
        ).order_by(Slave.market_price.asc()).limit(10)
    )
    slaves = result.scalars().all()

    kb = InlineKeyboardBuilder()

    if not slaves:
        kb.button(text="🛒 Обычный рынок", callback_data="market")
        kb.button(text="🔙 Меню", callback_data="main_menu")
        kb.adjust(2)
        await callback.message.edit_text("🏪 <b>Рынок новичков</b>\n\nПока тут пусто.", reply_markup=kb.as_markup())
        return

    text = (
        f"🏪 <b>Рынок новичков</b>\n"
        f"🔒 Только для бедных и новеньких\n"
        f"📊 Макс. цена: 🪙 {Slave.NEWCOMER_MAX_PRICE:,.0f}\n"
        f"💰 Налог: {Slave.NEWCOMER_TAX * 100:.0f}%\n\n"
    )

    for s in slaves:
        cls_name, _ = s.slave_class
        rarity = RARITY_NAMES[s.rarity]
        price = min(s.market_price, Slave.NEWCOMER_MAX_PRICE)
        target_name = s.target.username if s.target else str(s.target_id)
        text += (
            f"{'─' * 25}\n👤 @{target_name}\n"
            f"📊 Ур. {s.level} | {cls_name} | {rarity}\n"
            f"💵 🪙 {s.income_per_hour:,.2f}/час | 💲 🪙 {price:,.0f}\n"
        )
        kb.button(text=f"🛒 @{target_name} 🪙{price:,.0f}", callback_data=f"nbuy_{s.id}")

    kb.button(text="🛒 Обычный рынок", callback_data="market")
    kb.button(text="🔙 Меню", callback_data="main_menu")
    kb.adjust(1)
    await callback.message.edit_text(text, reply_markup=kb.as_markup())


@router.callback_query(F.data.startswith("nbuy_"))
async def buy_newcomer(callback: CallbackQuery, db):
    slave_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id

    slave = await db.get(Slave, slave_id)
    if not slave or not slave.newcomer_market:
        await callback.answer("Уже продан", show_alert=True)
        return

    user = await db.get(User, user_id)
    allowed, reason = is_newcomer_buyer(user)
    if not allowed:
        await callback.answer(reason, show_alert=True)
        return

    price = min(slave.market_price, Slave.NEWCOMER_MAX_PRICE)
    tax = calc_tax(price, Slave.NEWCOMER_TAX)
    seller_gets = price - tax

    if user.balance < price:
        await callback.answer(f"❌ Нужно 🪙 {price:,.0f}", show_alert=True)
        return

    if slave.last_bought_at:
        cooldown_end = slave.last_bought_at + timedelta(hours=Slave.NEWCOMER_COOLDOWN_HOURS)
        if datetime.utcnow() < cooldown_end:
            await callback.answer("⏳ Этот раб на кулдауне", show_alert=True)
            return

    seller = await db.get(User, slave.owner_id)
    user.balance -= price
    seller.balance += seller_gets
    slave.owner_id = user_id
    slave.newcomer_market = False
    slave.last_bought_at = datetime.utcnow()
    await db.commit()

    cls_name, _ = slave.slave_class
    target_name = slave.target.username if slave.target else str(slave.target_id)

    kb = InlineKeyboardBuilder()
    kb.button(text="👤 Мои рабы", callback_data="my_slaves")
    kb.button(text="🏪 Ещё", callback_data="newcomer_market")
    kb.button(text="🔙 Меню", callback_data="main_menu")
    kb.adjust(2)
    await callback.message.edit_text(
        f"✅ <b>Куплен на рынке новичков!</b>\n👤 @{target_name}\n"
        f"📊 {cls_name} | Ур. {slave.level}\n"
        f"💵 🪙 {slave.income_per_hour:,.2f}/час\n💸 🪙 {price:,.0f} | 🔥 Налог 🪙 {tax:,.0f}",
        reply_markup=kb.as_markup()
    )
    await callback.answer("✅ Куплено!")