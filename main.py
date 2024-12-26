import asyncio

from aiogram import Bot, Dispatcher
from config_data.config import Config, load_config
from database.database import init_db
from handlers.user import user_router

from aiogram.utils.callback_answer import CallbackAnswerMiddleware


async def main():
    config: Config = load_config()

    bot = Bot(token=config.tg_bot.token)
    dp = Dispatcher()
    dp.include_router(user_router)
    dp.callback_query.middleware(CallbackAnswerMiddleware())
    await init_db()

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

asyncio.run(main())
