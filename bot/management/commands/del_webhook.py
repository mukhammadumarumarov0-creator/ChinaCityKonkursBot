# bot/management/commands/del_webhook.py

import asyncio
from django.core.management.base import BaseCommand
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from django.conf import settings


class Command(BaseCommand):
    help = "Delete telegram webhook and drop pending updates"

    def handle(self, *args, **kwargs):
        asyncio.run(self.delete_webhook())

    async def delete_webhook(self):
        bot = Bot(
            token=settings.BOT_TOKEN,
            default=DefaultBotProperties(parse_mode="HTML")
        )

        try:
            info = await bot.get_webhook_info()
            self.stdout.write(f"Current webhook: {info.url}")

            if info.url:
                await bot.delete_webhook(drop_pending_updates=True)
                self.stdout.write(self.style.SUCCESS("✅ Webhook deleted"))
            else:
                self.stdout.write("ℹ️ Webhook mavjud emas")

        finally:
            await bot.session.close()
