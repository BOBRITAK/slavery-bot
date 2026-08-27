from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select
from models import Slave, User, RARITY_NAMES
from utils.plural import plural_rabs

router = Router()


@router.callback_query(F.data == "my_slaves")
async def my_slaves(callback: CallbackQuery, db):
    result = await db.execute(select(Slave).where(Slave.owner_id == callback.from_user.id))
    slaves = result.scalars().all()

    if not slaves:
        kb = InlineKeyboardBuilder()
        kb.button(text="🛒 На рынок", callback_data="market")
        kb.button(text="🔙 Меню", callback_data="main_menu")
        kb.adjust(2)
        await callback.message.edit_text("У тебя пока нет рабов. Загляни на рынок! 🛒", reply_markup=kb.as_markup())
        return

    total_income = sum(s.income_per_hour for s in slaves)
    text = f"⛓️ <b>Твои рабы</b> ({len(slaves)} {plural_rabs(len(slaves))})\n💰 Доход: 🪙 {total_income:,.2f}/час\n\n"

    kb = InlineKeyboardBuilder()
    for s in slaves:
        cls_name, _ = s.slave_class
        target_name = s.target.username if s.target else str(s.target_id)
        text += (
            f"{'─' * 25}\n"
            f"👤 @{target_name}\n"
            f"📊 Ур. {s.level} | {cls_name} | {RARITY_NAMES[s.rarity]}\n"
            f"💵 🪙 {s.income_per_hour:,.2f}/час\n"
        )
        kb.button(text=f"⬆️ @{target_name} (🪙{s.next_upgrade_cost:,.0f})", callback_data=f"upgrade_{s.id}")

    kb.button(text="🔙 Меню", callback_data="main_menu")
    kb.adjust(1)
    await callback.message.edit_text(text, reply_markup=kb.as_markup())


@router.callback_query(F.data.startswith("upgrade_"))
async def upgrade_slave(callback: CallbackQuery, db):
    slave_id = int(callback.data.split("_")[1])
    slave = await db.get(Slave, slave_id)

    if not slave:
        await callback.answer("Раб не найден", show_alert=True)
        return
    if slave.owner_id != callback.from_user.id:
        await callback.answer("❌ Прокачивать может только хозяин!", show_alert=True)
        return
    if slave.level >= 50:
        await callback.answer("❌ Максимальный уровень (50)!", show_alert=True)
        return

    user = await db.get(User, callback.from_user.id)
    cost = slave.next_upgrade_cost

    if user.balance < cost:
        await callback.answer(f"❌ Нужно 🪙 {cost:,.0f}, у тебя 🪙 {user.balance:,.0f}", show_alert=True)
        return

    old_class, _ = slave.slave_class
    user.balance -= cost
    slave.level += 1
    new_class, _ = slave.slave_class
    await db.commit()

    msg = (
        f"⬆️ <b>Прокачано до {slave.level} ур.</b>\n"
        f"💸 Потрачено: 🪙 {cost:,.0f}\n"
        f"📈 Доход: 🪙 {slave.income_per_hour:,.2f}/час\n"
        f"⏭️ Следующая: 🪙 {slave.next_upgrade_cost:,.0f}"
    )
    if old_class != new_class:
        msg += f"\n\n🎉 <b>НОВЫЙ КЛАСС: {new_class}!</b>"

    kb = InlineKeyboardBuilder()
    kb.button(text="⬆️ Ещё", callback_data=f"upgrade_{slave.id}")
    kb.button(text="👤 Мои рабы", callback_data="my_slaves")
    kb.button(text="🔙 Меню", callback_data="main_menu")
    kb.adjust(2)
    await callback.message.edit_text(msg, reply_markup=kb.as_markup())
    await callback.answer("✅ Прокачано!")