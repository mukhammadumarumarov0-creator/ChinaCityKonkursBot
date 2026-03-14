import re
from asgiref.sync import sync_to_async
from aiogram.types import ChatMember
from decouple import config
from bot.models import User, LiveParticipant, LiveSession
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot.instance.handlers.conf import BOT
from urllib.parse import urlparse
from django.core.exceptions import ObjectDoesNotExist
from .conf import KANALAR


# ================= USER =================
def get_user_sync(telegram_id: int) -> User | None:
    return User.objects.filter(telegram_id=telegram_id).first()


async def is_registered(telegram_id: int) -> User | None:
    return await sync_to_async(get_user_sync)(telegram_id)


async def create_user(telegram_id: int, full_name: str, phone: str, inviter=None) -> User:
    user, created = await sync_to_async(User.objects.get_or_create)(
        telegram_id=telegram_id,
        defaults={
            "full_name": full_name,
            "phone": phone,
            "inviter": inviter
        }
    )
    return user


# ================= CHANNEL =================
def _normalize_channel(kanal: str) -> str:
    """Istalgan formatni (url yoki @username) @username ga o'tkazadi."""
    if kanal.startswith("https://t.me/") or kanal.startswith("http://t.me/"):
        username = kanal.split("t.me/")[-1].strip("/")
        return f"@{username}"
    return kanal  # allaqachon @username yoki -100xxx formatida


async def check_channel_membership(user_id: int, bot=BOT) -> bool:
    """Foydalanuvchi BARCHA kanallarga a'zo ekanini tekshiradi."""
    for kanal in KANALAR:
        normalized = _normalize_channel(kanal)
        try:
            member: ChatMember = await bot.get_chat_member(chat_id=normalized, user_id=user_id)
            if member.status in ["left", "kicked", "banned"]:
                return False
        except Exception as e:
            print(f"[check_channel_membership] Xato user_id={user_id}, kanal={normalized}: {e}")
            return False
    return True


async def get_unsubscribed_channels(user_id: int, bot=BOT) -> list[str]:
    """Foydalanuvchi a'zo bo'lmagan kanallar ro'yxatini qaytaradi."""
    unsubscribed = []
    for kanal in KANALAR:
        normalized = _normalize_channel(kanal)
        try:
            member: ChatMember = await bot.get_chat_member(chat_id=normalized, user_id=user_id)
            if member.status in ["left", "kicked", "banned"]:
                unsubscribed.append(kanal)  # original format — URL uchun
        except Exception as e:
            print(f"[get_unsubscribed_channels] Xato kanal={normalized}: {e}")
            unsubscribed.append(kanal)
    return unsubscribed


# ================= VALIDATION =================
FULLNAME_ERROR = (
    "❌ Ism va familiyani to'g'ri kiriting.\n"
    "Masalan: Muhammad Umarov"
)

PHONE_ERROR = (
    "❌ Telefon raqam noto'g'ri.\n"
    "Namuna: +998901234567\n"
    "Yoki 📞 tugmani bosing"
)

FULL_NAME_REGEX = re.compile(
    r"^[A-Za-zА-Яа-яЎўҚқҒғҲҳЁё]+(?:[''][A-Za-zА-Яа-яЎўҚқҒғҲҳЁё]+)?"
    r"\s"
    r"[A-Za-zА-Яа-яЎўҚқҒғҲҳЁё]+(?:[''][A-Za-zА-Яа-яЎўҚқҒғҲҳЁё]+)?$"
)

PHONE_REGEX = re.compile(r"^\+998(90|91|93|94|95|97|98|99|33|88)\d{7}$")


def validate_full_name(full_name: str) -> bool:
    return bool(FULL_NAME_REGEX.fullmatch(full_name.strip()))


def normalize_phone(phone: str) -> str | None:
    digits = re.sub(r"\D", "", phone)

    if digits.startswith("998") and len(digits) == 12:
        digits = "+" + digits
    elif digits.startswith("9") and len(digits) == 9:
        digits = "+998" + digits
    elif not digits.startswith("+"):
        return None

    return digits if PHONE_REGEX.fullmatch(digits) else None


# ================= STAFF =================
def is_staff_sync(telegram_id: int) -> User | None:
    user = User.objects.filter(telegram_id=telegram_id).first()
    if user and (user.is_staff or user.is_superuser):
        return user
    return None


async def is_staff_async(telegram_id: int) -> User | None:
    return await sync_to_async(is_staff_sync)(telegram_id)


async def is_user_active(telegram_id: int) -> bool:
    user = await sync_to_async(
        User.objects.filter(telegram_id=telegram_id).first
    )()
    return bool(user and user.is_active)


# ================= KEYBOARD =================
def subscribe_keyboard(channels: list[str] | None = None):
    """Har bir kanal uchun alohida tugma + tasdiqlash tugmasi."""
    kb = InlineKeyboardBuilder()

    target = channels or KANALAR
    for kanal in target:
        if kanal.startswith("https://t.me/") or kanal.startswith("http://t.me/"):
            url = kanal
            name = "@" + kanal.split("t.me/")[-1].strip("/")
        else:
            username = kanal.lstrip("@")
            url = f"https://t.me/{username}"
            name = f"@{username}"

        kb.button(
            text=f"📢 {name} kanalga a'zo bo'ling",
            url=url
        )

    kb.button(text="✅ A'zo bo'ldim", callback_data="added")
    kb.adjust(1)
    return kb.as_markup()


# ================= USERS =================
async def get_all_users() -> list[int]:
    return await sync_to_async(list)(
        User.objects.filter(
            is_staff=False,
            is_active=True,
            telegram_id__isnull=False
        ).values_list('telegram_id', flat=True)
    )


@sync_to_async
def get_user_by_telegram_id(telegram_id: int) -> User | None:
    try:
        return User.objects.get(telegram_id=telegram_id)
    except User.DoesNotExist:
        return None


@sync_to_async
def get_all_user_ids() -> list[int]:
    return list(
        User.objects
        .filter(is_active=True)
        .exclude(telegram_id__isnull=True)
        .values_list("telegram_id", flat=True)
    )


# ================= LIVE =================
@sync_to_async
def has_joined_live(user: User, live: LiveSession) -> bool:
    return LiveParticipant.objects.filter(user=user, live=live).exists()


@sync_to_async
def mark_live_joined(user: User, live: LiveSession):
    LiveParticipant.objects.get_or_create(user=user, live=live)


async def add_live_points(user: User, live: LiveSession, points: int = 5) -> bool:
    if await has_joined_live(user, live):
        return False

    await user.add_referral_points_async(points)
    await mark_live_joined(user, live)
    return True


async def get_session(session_id: int) -> LiveSession | None:
    try:
        return await sync_to_async(LiveSession.objects.get)(id=session_id)
    except ObjectDoesNotExist:
        return None


async def parse_live_url(url: str) -> str | None:
    try:
        parsed = urlparse(url)

        if parsed.netloc not in ("t.me", "www.t.me"):
            return None

        parts = parsed.path.strip("/").split("/")
        if not parts or not parts[0]:
            return None

        username = parts[0]
        return f"@{username}"

    except Exception as e:
        print(f"[parse_live_url] Xato: {e}")
        return None