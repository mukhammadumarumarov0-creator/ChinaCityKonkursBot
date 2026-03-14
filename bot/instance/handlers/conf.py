from aiogram import Bot
from decouple import config

PHOTO_URL = config("PHOTO_URL")
BOT = Bot(token=config("BOT_TOKEN"))
BALL_FOR_USER = config("BALL_FOR_USER")
BALL_FOR_CHENEL = config("BALL_FOR_CHENEL")
_kanalar_raw = config("KANALAR")
KANALAR: list[str] = [k.strip() for k in _kanalar_raw.split(",") if k.strip()]

