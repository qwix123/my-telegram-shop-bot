# utils.py

import os
import asyncio
from aiogram import Bot
from aiogram.types import FSInputFile, InputMediaPhoto, Message, CallbackQuery

BANNER_PATH = "banner.png"

def get_banner():
    """Возвращает FSInputFile баннера если файл существует"""
    if os.path.exists(BANNER_PATH):
        return FSInputFile(BANNER_PATH)
    return None

async def send_menu(message: Message, text: str, reply_markup=None):
    """Отправляет новое сообщение с баннером и текстом"""
    banner = get_banner()
    if banner:
        return await message.answer_photo(
            photo=banner,
            caption=text,
            reply_markup=reply_markup
        )
    return await message.answer(text, reply_markup=reply_markup)

async def edit_menu(callback: CallbackQuery, text: str, reply_markup=None):
    """
    Редактирует сообщение (текст+баннер).
    Если сообщение с фото — редактирует caption.
    Если текстовое — пробует заменить на фото.
    """
    banner = get_banner()

    if callback.message.photo:
        try:
            await callback.message.edit_caption(
                caption=text,
                reply_markup=reply_markup
            )
            return callback.message.message_id
        except Exception as ex:
            print(f"⚠️ edit_caption: {ex}")

    if banner:
        try:
            await callback.message.edit_media(
                media=InputMediaPhoto(media=banner, caption=text),
                reply_markup=reply_markup
            )
            return callback.message.message_id
        except Exception:
            pass

    try:
        await callback.message.edit_text(text, reply_markup=reply_markup)
        return callback.message.message_id
    except Exception:
        pass

    if banner:
        msg = await callback.message.answer_photo(banner, caption=text, reply_markup=reply_markup)
    else:
        msg = await callback.message.answer(text, reply_markup=reply_markup)
    return msg.message_id

async def edit_menu_by_id(bot: Bot, chat_id: int, message_id: int, text: str, reply_markup=None):
    """Редактирует сообщение по chat_id + message_id"""
    banner = get_banner()

    try:
        await bot.edit_message_caption(
            chat_id=chat_id,
            message_id=message_id,
            caption=text,
            reply_markup=reply_markup
        )
        return message_id
    except Exception:
        pass

    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            reply_markup=reply_markup
        )
        return message_id
    except Exception:
        pass

    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass

    if banner:
        msg = await bot.send_photo(chat_id, banner, caption=text, reply_markup=reply_markup)
    else:
        msg = await bot.send_message(chat_id, text, reply_markup=reply_markup)
    return msg.message_id

# ---------- НОВАЯ ФУНКЦИЯ ДЛЯ НАПОМИНАНИЙ ----------
async def remind_about_payment(order_id: int, user_id: int, bot: Bot, delay: int = 900):
    """
    Отправляет напоминание о неоплаченном заказе через delay секунд.
    Завершается, если заказ уже оплачен.
    """
    await asyncio.sleep(delay)
    from database import Database
    db = Database()
    order = db.get_order(order_id)
    if order and order['payment_status'] == 'unpaid' and order['status'] == 'pending':
        try:
            from emoji_manager import e
            text = (
                f"{e('clock')} <b>Напоминание о заказе #{order_id}</b>\n\n"
                f"<blockquote>"
                f"{e('lightning')} Вы ещё не оплатили заказ.\n"
                f"{e('fire')} Пожалуйста, оплатите его в ближайшее время.\n\n"
                f"{e('rocket')} <b>Чтобы оплатить, перейдите в раздел «Мои заказы».</b>"
                f"</blockquote>\n"
                f"\n"
                f"{e('cart')} /start — главное меню"
            )
            await bot.send_message(user_id, text)
        except Exception as e:
            print(f"Ошибка отправки напоминания: {e}")