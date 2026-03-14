import asyncio
from aiogram.types import (Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton)
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from aiogram import Router, F
from asgiref.sync import sync_to_async
from django.core.exceptions import ObjectDoesNotExist
from .conf import BOT
from bot.models import User, LiveParticipant, LiveSession
from .bottens import face_button_for_admin_callback
from .utils import is_registered, get_session, parse_live_url, get_all_users


admin_router = Router()


# ================= STATES =================
class SendMessageState(StatesGroup):
    content = State()
    confirm = State()


# ================= START =================
@admin_router.message(F.text == "💬Mijozlarga xabar yuborish")
async def start_send(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "📝 Yuboriladigan xabarni yuboring:\n\n"
        "• 💬 Matn\n"
        "• 🖼 Rasm\n"
        "• 🎬 Video\n"
        "• ⭕ Dumaloq video\n"
        "• 🎵 Audio\n"
        "• 🎤 Ovozli xabar\n"
        "• 📄 Fayl"          # ✅ yangi
    )
    await state.set_state(SendMessageState.content)


@admin_router.message(SendMessageState.content)
async def preview(message: Message, state: FSMContext):
    data = {}
    preview_text = ""

    if message.text:
        data = {
            "type": "text",
            "text": message.text,
            "reply_markup": message.reply_markup
        }
        preview_text = message.text

    elif message.photo:
        data = {
            "type": "photo",
            "file_id": message.photo[-1].file_id,
            "caption": message.caption,
            "reply_markup": message.reply_markup
        }
        preview_text = "🖼 Rasm yuboriladi"

    elif message.video:
        data = {
            "type": "video",
            "file_id": message.video.file_id,
            "caption": message.caption,
            "reply_markup": message.reply_markup
        }
        preview_text = "🎬 Video yuboriladi"

    elif message.video_note:
        data = {
            "type": "video_note",
            "file_id": message.video_note.file_id,
            "reply_markup": message.reply_markup
        }
        preview_text = "⭕ Dumaloq video yuboriladi"

    elif message.audio:
        data = {
            "type": "audio",
            "file_id": message.audio.file_id,
            "caption": message.caption,
            "reply_markup": message.reply_markup
        }
        preview_text = "🎵 Audio yuboriladi"

    elif message.voice:
        data = {
            "type": "voice",
            "file_id": message.voice.file_id,
            "caption": message.caption,
            "reply_markup": message.reply_markup
        }
        preview_text = "🎤 Ovozli xabar yuboriladi"

    elif message.document:                          # ✅ yangi
        data = {
            "type": "document",
            "file_id": message.document.file_id,
            "caption": message.caption,
            "file_name": message.document.file_name or "fayl",
            "reply_markup": message.reply_markup
        }
        preview_text = f"📄 Fayl yuboriladi: <b>{message.document.file_name or 'fayl'}</b>"

    else:
        await message.answer("❌ Qo'llab-quvvatlanmaydigan format")
        return

    await state.update_data(**data)
    await state.set_state(SendMessageState.confirm)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="send"),
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel")
        ]]
    )

    await message.answer(
        f"📨 Tasdiqlang:\n\n{preview_text}",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


# ================= CANCEL =================
@admin_router.callback_query(F.data == "cancel")
async def cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Xabar yuborish bekor qilindi.")
    await callback.answer()


# ================= CONFIRM =================
@admin_router.callback_query(F.data == "send")
async def confirm(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.clear()

    user_ids = [uid for uid in await get_all_users() if uid]

    await callback.message.edit_text("🚀 Xabar yuborish boshlandi...")
    await callback.answer()

    await send_messages_background(data, user_ids)
    await BOT.send_message(
        callback.from_user.id,
        "✅ Xabar yuborish yakunlandi."
    )


async def send_safe(user_id: int, data: dict):
    try:
        if data["type"] == "text":
            await BOT.send_message(
                user_id,
                data["text"],
                parse_mode="HTML",
                reply_markup=data.get("reply_markup")
            )

        elif data["type"] == "photo":
            await BOT.send_photo(
                user_id,
                data["file_id"],
                caption=data.get("caption"),
                parse_mode="HTML",
                reply_markup=data.get("reply_markup")
            )

        elif data["type"] == "video":
            await BOT.send_video(
                user_id,
                data["file_id"],
                caption=data.get("caption"),
                parse_mode="HTML",
                reply_markup=data.get("reply_markup")
            )

        elif data["type"] == "audio":
            await BOT.send_audio(
                user_id,
                data["file_id"],
                caption=data.get("caption"),
                parse_mode="HTML",
                reply_markup=data.get("reply_markup")
            )

        elif data["type"] == "video_note":
            await BOT.send_video_note(
                user_id,
                data["file_id"],
                reply_markup=data.get("reply_markup")
            )

        elif data["type"] == "voice":
            await BOT.send_voice(
                user_id,
                data["file_id"],
                caption=data.get("caption"),
                parse_mode="HTML",
                reply_markup=data.get("reply_markup")
            )

        elif data["type"] == "document":               # ✅ yangi
            await BOT.send_document(
                user_id,
                data["file_id"],
                caption=data.get("caption"),
                parse_mode="HTML",
                reply_markup=data.get("reply_markup")
            )

        return 1, 0

    except TelegramForbiddenError:
        return 0, 1
    except TelegramBadRequest:
        return 0, 0
    except Exception as e:
        print(f"⚠️ Error for {user_id}: {e}")
        return 0, 0


async def send_messages_background(data: dict, user_ids: list[int]):
    success = 0
    blocked = 0

    for i in range(0, len(user_ids), 20):
        batch = user_ids[i:i + 20]

        results = await asyncio.gather(
            *(send_safe(uid, data) for uid in batch)
        )

        for s, b in results:
            success += s
            blocked += b

        await asyncio.sleep(0.5)

    print(f"✅ DONE | success={success} blocked={blocked}")


# ================= STATES =================
class StartLive(StatesGroup):
    url = State()
    confirm = State()


# ================= START LIVE =================
@admin_router.message(F.text == "Jonli Efir 📺")
async def start_live(message: Message, state: FSMContext):
    user = await is_registered(message.from_user.id)
    if user and (user.is_staff or user.is_superuser):
        await state.clear()
        await state.set_state(StartLive.url)
        await message.answer(text="📎 <b>Jonli efir URL ni kiriting:</b>", parse_mode="HTML")


# ================= URL PREVIEW =================
@admin_router.message(StartLive.url)
async def preview_live(message: Message, state: FSMContext):
    url = message.text.strip()

    if not url.startswith("http"):
        await message.answer("❌ URL noto'g'ri")
        return

    await state.update_data(url=url)
    await state.set_state(StartLive.confirm)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="✅ Kanalga yuborish", callback_data="live:confirm"),
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data="live:cancel")
        ]]
    )

    await message.answer(
        text=f"📺 <b>Jonli efir URL:</b>\n\n{url}",
        parse_mode="HTML",
        reply_markup=keyboard
    )


# ================= CANCEL LIVE =================
@admin_router.callback_query(F.data.startswith("live:cancel"))
async def cancel_live(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(text="❌ <b>Jonli efir bekor qilindi</b>", parse_mode="HTML")
    await callback.answer()


# ================= SEND TO CHANNEL =================
@admin_router.callback_query(F.data == "live:confirm")
async def send_live_to_channel(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    live_url = data.get("url")

    if not live_url:
        await callback.answer(text="❌ URL topilmadi", show_alert=True)
        return

    KANAL = await parse_live_url(live_url)

    live_session = await sync_to_async(LiveSession.objects.create)()

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(
                text="📺 Jonli efirga qo'shilish",
                callback_data=f"live_join_{live_session.pk}"
            )
        ]]
    )

    keyboard_live_cancel = InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(
                text="📺 Yakunlash",
                callback_data=f"finish:live:{live_session.pk}"
            )
        ]]
    )

    text = (
        "🎉 <b>Jonli efir boshlandi!</b>\n\n"
        "👇 Tugma orqali kiring\n\n"
        "⭐ <b>+5 ball</b> faqat bir marta beriladi"
    )

    await callback.answer()
    try:
        await BOT.send_message(
            chat_id=KANAL,
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        await callback.message.edit_text(
            text="Jonli Efir bo'lmoqda uni yakunlash uchun\n👇 Pastegi yakunlash tumasini bo'sing",
            reply_markup=keyboard_live_cancel
        )
    except Exception as e:
        print("LIVE SEND ERROR:", e)
        await callback.answer("❌ Kanalga yuborilmadi", show_alert=True)

    await state.clear()


# ================= USER JOIN LIVE =================
@admin_router.callback_query(F.data.startswith("live_join"))
async def join_live(callback: CallbackQuery):
    print("kirdi")

    live_session_id = int(callback.data.split("_")[-1])
    telegram_id = callback.from_user.id
    print(telegram_id)
    live_session = await get_session(live_session_id)

    try:
        user = await sync_to_async(User.objects.get)(telegram_id=telegram_id)
        print(user)
    except ObjectDoesNotExist:
        await callback.answer(text="❌ Siz botda ro'yxatdan o'tmagansiz", show_alert=True)
        return

    if live_session and (not live_session.is_active):
        await callback.answer(text="📺 Jonli Efir Yakunlangan", show_alert=True)
        return

    already_joined = await sync_to_async(
        LiveParticipant.objects.filter(user=user, live=live_session).exists
    )()

    if already_joined:
        await callback.answer(text="⚠️ Siz allaqachon qatnashgansiz", show_alert=True)
        return

    await sync_to_async(LiveParticipant.objects.create)(user=user, live=live_session)
    await user.add_referral_points_async(5)
    await callback.answer(text="🎉 +5 ball qo'shildi!", show_alert=True)


# ================= FINISH LIVE =================
@admin_router.callback_query(F.data.startswith("finish:live"))
async def stop_live_session(callback: CallbackQuery, state: FSMContext):
    session_id = int(callback.data.split(":")[-1])
    live_session = await get_session(session_id=session_id)

    if live_session:
        live_session.is_active = False
        await sync_to_async(live_session.save)()
        await callback.message.delete()
        await callback.answer()
        await face_button_for_admin_callback(
            callback=callback,
            text="Jonli efir to'xtatildi ✅"
        )
    else:
        await callback.answer("❌ Jonli efir topilmadi", show_alert=True)