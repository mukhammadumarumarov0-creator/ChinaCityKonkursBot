from aiogram import Router, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest
from asgiref.sync import sync_to_async
from aiogram.types import Message
import asyncio

from .conf import PHOTO_URL, BALL_FOR_CHENEL, BALL_FOR_USER
from bot.models import User
from .service import write_user_to_sheet_bg
from bot.instance.handlers.messages import (
    welcome_message, meeting_message, admin_connect, ask_name_message, ask_phone_message,
    gift_caption, rules_caption, share_message_ref, message_text, obunaMatni, welcomeAdminMatni,
    message_for_intro, message_for_meeting)

from bot.instance.handlers.utils import (
    validate_full_name, FULLNAME_ERROR, PHONE_ERROR, normalize_phone,
    is_registered, check_channel_membership, create_user,
    get_unsubscribed_channels, subscribe_keyboard)

from bot.instance.handlers.bottens import (
    register_button, phone_button,
    face_button, face_button_for_admin,add_kb)


user_router = Router()


class RegisterProcess(StatesGroup):
    full_name = State()
    phone = State()


@user_router.message(CommandStart())
async def start_handler(message: Message, state: FSMContext):
    try:
        user = await is_registered(message.from_user.id)

        if user and (user.is_staff or user.is_superuser):
            await face_button_for_admin(message=message, text=welcomeAdminMatni)
            return

        args = message.text.split()
        inviter_id = None

        if len(args) > 1 and args[1].startswith("ref_"):
            try:
                ref_id = int(args[1].replace("ref_", ""))
                if ref_id != message.from_user.id:
                    inviter_id = ref_id
            except ValueError:
                pass

        intro_message = (
            f"<b>👋 Assalomu Alaykum {message.from_user.first_name or ''}! Xush kelibsiz!</b>\n"
            "<i>China City</i> kanalida sizni <b>qiziqarli konkurslar</b> va <b>sovrinlar 🎁✨</b> kutmoqda!\n\n"
            "<u>Kanalga obuna bo'ling va ishtirok eting!</u>"
        )

        try:
            is_member = await check_channel_membership(user_id=message.from_user.id)
        except Exception as e:
            print(f"Kanal tekshirishda xato (start): {e}")
            is_member = False

        if not is_member:
            await state.update_data(inviter_id=inviter_id)
            await message.answer(text=message_for_intro, parse_mode="HTML")
            await message.answer(
                text=intro_message,
                reply_markup=subscribe_keyboard(),
                parse_mode="HTML"
            )
            return

        if user:
            await face_button(message, text=welcome_message)
            return

        await state.update_data(inviter_id=inviter_id)
        
        await register_button(message, message_for_meeting)

    except Exception as e:
        print(f"start_handler xatosi: {e}")
        await message.answer("❌ Xatolik yuz berdi. Iltimos, qaytadan /start bosing.")


@user_router.message(F.text == "📃 Ro'yhatdan o'tish")
async def start_register(message: Message, state: FSMContext):
    try:
        if not await is_registered(message.from_user.id):
            await state.set_state(RegisterProcess.full_name)
            await message.answer(ask_name_message, parse_mode="HTML")
    except Exception as e:
        print(f"start_register xatosi: {e}")
        await message.answer("❌ Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.")


@user_router.message(RegisterProcess.full_name)
async def fullname_register(message: Message, state: FSMContext):
    try:
        if not message.text or not validate_full_name(message.text):
            await message.answer(FULLNAME_ERROR, parse_mode="HTML")
            return

        await state.update_data(full_name=message.text)
        await state.set_state(RegisterProcess.phone)
        await phone_button(message, ask_phone_message)

    except Exception as e:
        print(f"fullname_register xatosi: {e}")
        await message.answer("❌ Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.")


@user_router.message(RegisterProcess.phone)
async def phone_register(message: types.Message, state: FSMContext):
    try:
        phone = None
        if message.contact:
            phone = message.contact.phone_number
        elif message.text:
            phone = message.text

        if not phone:
            await message.answer(PHONE_ERROR)
            return

        normalized = normalize_phone(phone)
        if not normalized:
            await message.answer(PHONE_ERROR)
            return

        data = await state.get_data()
        full_name = data.get("full_name")

        if not full_name:
            await message.answer("❌ Xatolik yuz berdi. Iltimos, qaytadan boshlang.")
            await state.clear()
            return

        inviter_id = data.get("inviter_id")

        existing_user = await sync_to_async(
            User.objects.filter(telegram_id=message.from_user.id).first
        )()
        if existing_user:
            await state.clear()
            await face_button(message, text=message_text)
            return

        inviter = None
        if inviter_id:
            try:
                inviter = await sync_to_async(
                    User.objects.filter(telegram_id=inviter_id).first
                )()
            except Exception as e:
                print(f"Inviter olishda xato: {e}")

        try:
            user = await create_user(
                full_name=full_name,
                phone=normalized,
                telegram_id=message.from_user.id,
                inviter=inviter
            )
        except Exception as e:
            print(f"User yaratishda xato: {e}")
            await message.answer("❌ Ro'yxatdan o'tishda xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.")
            return

        if inviter:
            try:
                ball = int(BALL_FOR_USER) if BALL_FOR_USER and int(BALL_FOR_USER) != 0 else 5
                await inviter.add_referral_points_async(ball)
            except (ValueError, TypeError) as e:
                print(f"BALL_FOR_USER xatosi: {e}")
                await inviter.add_referral_points_async(5)

        try:
            is_member = await check_channel_membership(user_id=message.from_user.id)
        except Exception as e:
            print(f"Kanal tekshirishda xato: {e}")
            is_member = False

        if is_member:
            try:
                ball = int(BALL_FOR_CHENEL) if BALL_FOR_CHENEL and int(BALL_FOR_CHENEL) != 0 else 10
                await user.add_referral_points_async(ball)
            except (ValueError, TypeError) as e:
                print(f"BALL_FOR_CHENEL xatosi: {e}")
                await user.add_referral_points_async(10)
        else:
            await message.answer(
                text=obunaMatni,
                reply_markup=subscribe_keyboard(),
                parse_mode="HTML"
            )
            await state.clear()
            return

        try:
            asyncio.create_task(write_user_to_sheet_bg(
                chat_id=message.from_user.id,
                username=message.from_user.username or "",
                full_name=full_name,
                phone=normalized
            ))
        except Exception as e:
            print(f"Google Sheets error: {e}")

        done_message = (
            f"🎉 Tabriklaymiz <b>{message.from_user.first_name}</b>!\n"
            "<b>✅ Ro'yxatdan muvaffaqiyatli o'tdingiz!</b>\n"
            "Endi siz botimizning barcha qulayliklaridan to'liq foydalanishingiz mumkin.\n\n"
        )

        await state.clear()
        await message.answer(done_message, parse_mode="HTML")
        await face_button(message, text=message_text)

    except Exception as e:
        print(f"phone_register xatosi: {e}")
        await state.clear()
        await message.answer("❌ Xatolik yuz berdi. Iltimos, /start bosib qaytadan boshlang.")


@user_router.message(F.text == "Konkursda qatnashish 🔴")
async def contest_handler(message: Message):
    try:
        user = await is_registered(message.from_user.id)

        if not user:
            await message.answer(
                "❌ Siz hali ro'yxatdan o'tmagansiz.\n"
                "Iltimos, tizimdan to'liq foydalanish uchun ro'yxatdan o'ting. 💛"
            )
            return

        link_message = (
            "🏠 <b>China City – Konkursi!</b>\n\n"
            "Salom! 🎉\n"
            "<b>China City</b> konkursi sizni taklif qilmoqda!\n\n"
            "🏆 <b>Sovg'alar:</b>\n"
            "🥇 <b>Top 5 eng ko'p ball </b> — 🧊 Muzlatgich\n"
            "🎲 <b>200+ ball </b> — 🫧 Kir yuvish mashinasi\n"
            "🎲 <b>150+ ball </b> — 📺 Televizor\n"
            "🎲 <b>100+ ball </b> — ❄️ Konditsioner\n"
            "🎲 <b>80+ ball </b> — 🧹 Changyutgich\n"
            "🎲 <b>60+ ball </b> — 🍳 Gaz plita\n"
            "🎲 <b>45+ ball </b> — 🥤 Blender\n"
            "🎲 <b>35+ ball </b> — 📱 Telefon\n"
            "🎲 <b>25+ ball </b> — 🔥 Mini pech\n"
            "🎁 <b>20+ ball </b> — ☕️ Elektr choynak\n\n"
            "⚡ Sovg'alar haqiqiy, qatnashish esa juda oson – sinab ko'ring! 😄\n\n"
            "👇 <b>Konkursga qatnashish uchun havola:</b>\n\n"
            f"  {user.get_invite_link()}\n\n\n"
        )

        await message.answer_photo(
            photo=PHOTO_URL,
            caption=link_message,
            parse_mode="HTML",
            reply_markup=add_kb(user.get_invite_link())
        )
        await message.answer(text=share_message_ref, parse_mode="HTML")

    except Exception as e:
        print(f"contest_handler xatosi: {e}")
        await message.answer("❌ Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.")


@user_router.message(F.text == "👤 Ballarim")
async def points_handler(message: Message):
    try:
        user = await is_registered(message.from_user.id)

        if not user:
            await message.answer(
                "❌ Siz hali ro'yxatdan o'tmagansiz.\n"
                "Iltimos, ro'yxatdan o'ting. 💛"
            )
            return

        score_message = (
            f"💡 <b>Siz to'plagan ball:</b> {user.referral_points}\n\n"
            "🔥 Ajoyib natija! Do'stlaringizni taklif qilishda davom eting —\n"
            "har bir yangi do'st sizni <b>g'oliblikka</b> bir qadam yaqinlashtiradi! ⚡️\n\n"
            "🎁 Sovg'a sizni kutmoqda!\n"
            "Har bir qadam — bu <b>yutuqqa</b> ochilgan yangi eshik! 🌟"
        )
        await message.answer(text=score_message, parse_mode="HTML")

    except Exception as e:
        print(f"points_handler xatosi: {e}")
        await message.answer("❌ Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.")


@user_router.message(F.text == "🎁 Sovg'alar")
async def gifts_handler(message: Message):
    try:
        await message.answer_photo(
            photo=PHOTO_URL,
            caption=gift_caption,
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"gifts_handler xatosi: {e}")
        await message.answer(gift_caption, parse_mode="HTML")


@user_router.message(F.text == "💡Shartlar")
async def rules_handler(message: Message):
    try:
        await message.answer_photo(
            photo=PHOTO_URL,
            caption=rules_caption,
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"rules_handler xatosi: {e}")
        await message.answer(rules_caption, parse_mode="HTML")


@user_router.message(F.text == "👤 Admin")
async def admin_btn_handler(message: types.Message):
    try:
        await message.answer(
            admin_connect,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    except Exception as e:
        print(f"admin_btn_handler xatosi: {e}")


@user_router.callback_query(F.data == "added")
async def check_subscribed(callback: types.CallbackQuery, state: FSMContext):
    try:
        unsubscribed = await get_unsubscribed_channels(user_id=callback.from_user.id)

        if unsubscribed:
            channels_text = "\n".join(unsubscribed)
            await callback.answer(
                f"❌ Hali quyidagi kanallarga a'zo bo'lmadingiz:\n{channels_text}",
                show_alert=True
            )
            # Markup o'zgarmagan bo'lsa xatoni ignore qilamiz
            try:
                await callback.message.edit_reply_markup(
                    reply_markup=subscribe_keyboard(unsubscribed)
                )
            except TelegramBadRequest as e:
                if "message is not modified" not in str(e):
                    raise
            return

        await callback.answer("✅ Barcha kanallarga obuna tasdiqlandi.", show_alert=True)

        user = await is_registered(callback.from_user.id)

        if user:
            # Registered → Dashboard
            await face_button(callback.message, text=welcome_message)
        else:
            # Not registered → Registration
            await register_button(callback.message, message_for_meeting)

    except Exception as e:
        print(f"check_subscribed xatosi: {e}")
        await callback.answer("❌ Xatolik yuz berdi. Qaytadan urinib ko'ring.", show_alert=True)