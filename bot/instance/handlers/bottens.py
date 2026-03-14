from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import CallbackQuery
from .conf import KANALAR


async def register_button(message: Message, text: str):
    """Ro'yhatdan o'tish tugmasini yuboradi"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📃 Ro'yhatdan o'tish")]],
        resize_keyboard=True
    )
    await message.answer(text=text, reply_markup=keyboard, parse_mode='HTML')


async def phone_button(message: Message, text: str):
    """Telefon raqam yuborish tugmasi"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📲 Raqam jo'natish", request_contact=True)]],
        resize_keyboard=True
    )
    await message.answer(text=text, reply_markup=keyboard, parse_mode='HTML')


btn_admin = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="👤 Admin bilan bog'lanish")]],
    resize_keyboard=True
)


async def face_button(message: Message, text: str):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Konkursda qatnashish 🔴")],
            [KeyboardButton(text="🎁 Sovg'alar"), KeyboardButton(text="👤 Ballarim")],
            [KeyboardButton(text="💡Shartlar"), KeyboardButton(text="👤 Admin")],
        ],
        resize_keyboard=True
    )
    await message.answer(text=text, reply_markup=keyboard, parse_mode='HTML')


async def face_button_for_admin(message: Message, text: str):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💬Mijozlarga xabar yuborish"), KeyboardButton(text="Jonli Efir 📺")]
        ], resize_keyboard=True
    )
    await message.answer(text=text, reply_markup=keyboard, parse_mode='HTML')


async def face_button_for_admin_callback(callback: CallbackQuery, text: str):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💬Mijozlarga xabar yuborish"), KeyboardButton(text="Jonli Efir 📺")]
        ], resize_keyboard=True
    )
    await callback.message.answer(text=text, reply_markup=keyboard, parse_mode='HTML')


def _get_url_and_name(kanal: str) -> tuple[str, str]:
    """Istalgan formatdan (url yoki @username) url va name qaytaradi."""
    if kanal.startswith("https://t.me/") or kanal.startswith("http://t.me/"):
        url = kanal
        name = "@" + kanal.split("t.me/")[-1].strip("/")
    else:
        username = kanal.lstrip("@")
        url = f"https://t.me/{username}"
        name = f"@{username}"
    return url, name


def subscribe_keyboard(channels: list[str] | None = None):
    """Har bir kanal uchun alohida tugma + tasdiqlash tugmasi."""
    kb = InlineKeyboardBuilder()

    target = channels or KANALAR
    for kanal in target:
        url, name = _get_url_and_name(kanal)
        kb.button(
            text=f"📢 {name} kanalga a'zo bo'ling",
            url=url
        )

    kb.button(text="✅ A'zo bo'ldim", callback_data="added")
    kb.adjust(1)
    return kb.as_markup()


def add_kb(link: str = None):
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Qo'shislish", url=link)
    builder.adjust(2)
    return builder.as_markup()