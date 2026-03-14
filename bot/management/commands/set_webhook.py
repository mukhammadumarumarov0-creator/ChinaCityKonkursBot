import asyncio
from django.core.management.base import BaseCommand
from aiogram import Bot
from config import settings

class Command(BaseCommand):
    help = "Set Telegram bot webhook"

    def handle(self, *args, **kwargs):
        asyncio.run(self.set_webhook())

    async def set_webhook(self):
        bot = Bot(token=settings.BOT_TOKEN)
        try:
            await bot.set_webhook(
                url=settings.BOT_WEBHOOK_URL,
                drop_pending_updates=True
            )
            print("✅ Webhook SET:", settings.BOT_WEBHOOK_URL)
        finally:
            await bot.session.close()
