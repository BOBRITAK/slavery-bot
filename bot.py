import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from sqlalchemy import select
from config import BOT_TOKEN
from database import engine, async_session
from models import Base, User
from handlers import menu, slaves, market, transfer, newcomer_market

logging.basicConfig(level=logging.INFO)


async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    @dp.message.middleware()
    @dp.callback_query.middleware()
    async def db_middleware(handler, event, data):
        async with async_session() as session:
            data["db"] = session
            if hasattr(event, "from_user") and event.from_user:
                result = await session.execute(select(User).where(User.id == event.from_user.id))
                user = result.scalar_one_or_none()
                if not user:
                    user = User(id=event.from_user.id, username=event.from_user.username, balance=100.0)
                    session.add(user)
                    await session.commit()
            return await handler(event, data)

    dp.include_router(menu.router)
    dp.include_router(slaves.router)
    dp.include_router(market.router)
    dp.include_router(transfer.router)
    dp.include_router(newcomer_market.router)

    logging.info("🚀 Бот запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())