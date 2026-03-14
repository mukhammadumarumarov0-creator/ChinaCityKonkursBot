from aiogram import Bot, Dispatcher, types
from bot.instance.handlers import user_router,admin_router
from bot.instance.handlers.conf import BOT

webhook_dp = Dispatcher()
webhook_dp.include_router(user_router)
webhook_dp.include_router(admin_router)


async def feed_update(token: str, update: dict):
    bot = BOT
    try:
        aiogram_update = types.Update(**update)
        await webhook_dp.feed_update(
            bot=bot,
            update=aiogram_update
        )
    finally:
        await bot.session.close()
