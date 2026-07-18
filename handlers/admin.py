# handlers/admin.py

import re
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from keyboards import after_purchase_keyboard, back_to_menu_keyboard, admin_order_keyboard
from config import ADMINS
from emoji_manager import e, apply_emoji_pack, reset_emojis
from database import Database
from utils import edit_menu_by_id, get_banner

router = Router()
db = Database()


class EmojiSetup(StatesGroup):
    waiting_pack = State()


class PromoSetup(StatesGroup):
    waiting_code = State()
    waiting_type = State()
    waiting_value = State()
    waiting_expires = State()
    waiting_max_uses = State()


# ═══════════════════════════════════════════════════════════
# 🔧 ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ
# ═══════════════════════════════════════════════════════════

async def edit_user_message(bot: Bot, order: dict, text: str, reply_markup=None):
    """Редактирует сообщение у пользователя с поддержкой фото."""
    chat_id = order.get('user_chat_id') or order['user_id']
    message_id = order.get('user_message_id')

    if message_id:
        new_id = await edit_menu_by_id(bot, chat_id, message_id, text, reply_markup)
        if new_id != message_id:
            db.set_user_message_id(order['id'], new_id, chat_id)
        return

    banner = get_banner()
    try:
        if banner:
            msg = await bot.send_photo(chat_id, banner, caption=text, reply_markup=reply_markup)
        else:
            msg = await bot.send_message(chat_id, text, reply_markup=reply_markup)
        db.set_user_message_id(order['id'], msg.message_id, chat_id)
    except Exception as ex:
        print(f"⚠️ Не удалось отправить пользователю: {ex}")


# ═══════════════════════════════════════════════════════════
# 🎨 УПРАВЛЕНИЕ ЭМОДЗИ
# ═══════════════════════════════════════════════════════════

@router.message(Command("setpack"))
async def cmd_setpack(message: Message, state: FSMContext):
    """Установить набор премиум-эмодзи"""
    if message.from_user.id not in ADMINS:
        return

    text = (
        f"{e('sparkle')} <b>Установка набора премиум-эмодзи</b>\n"
        f"\n"
        f"<blockquote>"
        f"{e('fire')} Отправьте <b>ссылку на набор</b> в формате:\n"
        f"<code>https://t.me/addemoji/НазваниеНабора</code>\n\n"
        f"{e('lightning')} Или просто <b>название</b> набора:\n"
        f"<code>MatrixFont</code>"
        f"</blockquote>\n"
        f"\n"
        f"<blockquote>"
        f"{e('diamond')} Бот автоматически подберёт эмодзи под каждую роль!"
        f"</blockquote>\n"
        f"\n"
        f"{e('cross')} Для отмены: /cancel"
    )
    await message.answer(text)
    await state.set_state(EmojiSetup.waiting_pack)


@router.message(Command("cancel"), EmojiSetup.waiting_pack)
async def cancel_setup(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(f"{e('cross')} <b>Установка отменена</b>")


@router.message(EmojiSetup.waiting_pack)
async def process_pack(message: Message, state: FSMContext, bot: Bot):
    text = message.text.strip()

    match = re.search(r'addemoji/([a-zA-Z0-9_]+)', text)
    if match:
        pack_name = match.group(1)
    else:
        pack_name = text.replace("@", "").strip()

    if not pack_name or not re.match(r'^[a-zA-Z0-9_]+$', pack_name):
        await message.answer(
            f"{e('cross')} <b>Неверный формат!</b>\n\n"
            f"<blockquote>"
            f"Отправьте ссылку или название набора:\n"
            f"<code>https://t.me/addemoji/MatrixFont</code>\n"
            f"или\n"
            f"<code>MatrixFont</code>"
            f"</blockquote>"
        )
        return

    loading = await message.answer(
        f"{e('lightning')} <b>Загружаю набор</b> <code>{pack_name}</code>...\n"
        f"{e('sparkle')} Анализирую эмодзи и подбираю оптимальные..."
    )

    result = await apply_emoji_pack(bot, pack_name)

    if not result['success']:
        error_text = (
            f"{e('cross')} <b>Ошибка загрузки!</b>\n\n"
            f"<blockquote>"
            f"<b>Причина:</b> {result['error']}"
            f"</blockquote>\n"
            f"\n"
            f"<blockquote>"
            f"{e('lightning')} Проверьте:\n"
            f"• Правильность названия набора\n"
            f"• Это именно набор премиум-эмодзи (не стикеров)\n"
            f"• Набор существует и доступен"
            f"</blockquote>"
        )
        if len(error_text) > 4000:
            error_text = error_text[:3970] + "\n... (сообщение сокращено)"
        await loading.edit_text(error_text)
        await state.clear()
        return

    matched = result['matched']
    pack_title = result['pack_title'][:50] + ('...' if len(result['pack_title']) > 50 else '')

    success_text = (
        f"{e('trophy')}{e('sparkle')} <b>НАБОР УСТАНОВЛЕН!</b> {e('sparkle')}{e('trophy')}\n"
        f"\n"
        f"<blockquote>"
        f"{e('crown')} <b>Название:</b> {pack_title}\n"
        f"{e('fire')} <b>Эмодзи в наборе:</b> {result['total_in_set']}\n"
        f"{e('check')} <b>Подобрано ролей:</b> {len(matched)}"
        f"</blockquote>\n"
        f"\n"
        f"<blockquote>"
        f"{e('rocket')} <b>Готово!</b> Все сообщения бота теперь используют новые эмодзи!"
        f"</blockquote>\n"
        f"\n"
        f"{e('lightning')} <b>Команды:</b>\n"
        f"/preview — посмотреть все эмодзи\n"
        f"/resetpack — сбросить на обычные"
    )

    if len(success_text) > 4000:
        success_text = success_text[:3970] + "\n... (сообщение сокращено)"

    await loading.edit_text(success_text)
    await state.clear()


@router.message(Command("preview"))
async def cmd_preview(message: Message):
    """Показать текущие эмодзи"""
    if message.from_user.id not in ADMINS:
        return

    role_names = {
        'star': 'Звезда',
        'fire': 'Огонь',
        'check': 'Галочка',
        'cross': 'Крестик',
        'diamond': 'Алмаз',
        'crown': 'Корона',
        'rocket': 'Ракета',
        'gift': 'Подарок',
        'money': 'Деньги',
        'cart': 'Корзина',
        'sparkle': 'Искры',
        'heart': 'Сердце',
        'medal': 'Медаль',
        'trophy': 'Кубок',
        'lightning': 'Молния',
    }

    lines = [f"{e('sparkle')} <b>ТЕКУЩИЕ ЭМОДЗИ БОТА</b> {e('sparkle')}\n"]
    lines.append("<blockquote>")

    for role_key, role_name in role_names.items():
        current_emoji = e(role_key)
        lines.append(f"{role_name}: {current_emoji}")

    lines.append("</blockquote>")
    lines.append(f"\n{e('lightning')} <b>Пример сообщения:</b>\n")

    example = (
        f"<blockquote>"
        f"{e('sparkle')}{e('diamond')} <b>Заказ #1234</b> {e('diamond')}{e('sparkle')}\n"
        f"{e('star')} Товар: Telegram Звёзды\n"
        f"{e('fire')} Количество: 100 шт.\n"
        f"{e('money')} Цена: 5.00 BYN\n"
        f"{e('check')} <b>Подтверждено!</b>\n"
        f"{e('rocket')} Спасибо за покупку!"
        f"</blockquote>"
    )
    lines.append(example)

    full_text = "\n".join(lines)
    if len(full_text) > 4000:
        full_text = full_text[:3970] + "\n... (сообщение сокращено)"
    await message.answer(full_text)


@router.message(Command("resetpack"))
async def cmd_resetpack(message: Message):
    """Сбросить эмодзи на обычные"""
    if message.from_user.id not in ADMINS:
        return

    reset_emojis()
    await message.answer(
        f"{e('check')} <b>Эмодзи сброшены!</b>\n\n"
        f"<blockquote>"
        f"Теперь используются обычные эмодзи.\n"
        f"Установить новый набор: /setpack"
        f"</blockquote>"
    )


@router.message(Command("emoji"))
async def get_emoji_ids(message: Message):
    """Получить ID премиум-эмодзи из сообщения"""
    if message.from_user.id not in ADMINS:
        return

    if not message.reply_to_message:
        await message.answer(
            f"{e('sparkle')} <b>Получение ID премиум-эмодзи</b>\n"
            f"\n"
            f"<blockquote>"
            f"1️⃣ Отправьте премиум-эмодзи\n"
            f"2️⃣ Ответьте на них командой /emoji\n\n"
            f"{e('fire')} Или используйте /setpack — установить целый набор автоматически!"
            f"</blockquote>"
        )
        return

    reply = message.reply_to_message
    if not reply.entities:
        await message.answer(f"{e('cross')} <b>В сообщении нет премиум-эмодзи</b>")
        return

    result = f"{e('sparkle')} <b>Найденные эмодзи:</b>\n\n<blockquote>"
    found = False

    for entity in reply.entities:
        if entity.type == "custom_emoji":
            emoji_char = reply.text[entity.offset:entity.offset + entity.length]
            result += f"{emoji_char} <code>{entity.custom_emoji_id}</code>\n"
            found = True

    result += "</blockquote>"

    if found:
        if len(result) > 4000:
            result = result[:3970] + "\n... (сообщение сокращено)"
        await message.answer(result)
    else:
        await message.answer(f"{e('cross')} <b>Премиум-эмодзи не найдены</b>")


@router.message(Command("help_admin"))
async def cmd_help_admin(message: Message):
    if message.from_user.id not in ADMINS:
        return

    text = (
        f"{e('crown')} <b>КОМАНДЫ АДМИНИСТРАТОРА</b>\n"
        f"\n"
        f"<blockquote>"
        f"{e('sparkle')} <b>Управление эмодзи:</b>\n"
        f"/setpack — установить набор премиум-эмодзи\n"
        f"/preview — посмотреть текущие эмодзи\n"
        f"/resetpack — сбросить на обычные\n"
        f"/emoji — получить ID эмодзи"
        f"</blockquote>\n"
        f"\n"
        f"<blockquote>"
        f"{e('lightning')} <b>Управление промокодами:</b>\n"
        f"/addpromo — создать промокод (пошагово)\n"
        f"/listpromo — список всех промокодов\n"
        f"/delpromo <код> — удалить промокод"
        f"</blockquote>\n"
        f"\n"
        f"<blockquote>"
        f"{e('rocket')} <b>Статистика:</b>\n"
        f"/stats — общая статистика"
        f"</blockquote>"
    )
    await message.answer(text)


# ═══════════════════════════════════════════════════════════
# 📊 СТАТИСТИКА
# ═══════════════════════════════════════════════════════════

@router.message(Command("stats"))
async def cmd_stats(message: Message):
    if message.from_user.id not in ADMINS:
        return

    stats = db.get_stats()
    all_users = db.get_all_users()
    refs = sum(1 for u in all_users if u.get('referred_by') is not None)

    text = (
        f"{e('trophy')}{e('sparkle')} <b>СТАТИСТИКА БОТА</b> {e('sparkle')}{e('trophy')}\n"
        f"\n"
        f"<blockquote>"
        f"{e('crown')} <b>Пользователей:</b> {stats['total_users']}\n"
        f"{e('cart')} <b>Всего заказов:</b> {stats['total_orders']}\n"
        f"{e('check')} <b>Выполнено:</b> {stats['completed_orders']}\n"
        f"{e('money')} <b>Выручка:</b> {stats['total_revenue']:.2f} BYN\n"
        f"{e('gift_box')} <b>Рефералов:</b> {refs}"
        f"</blockquote>"
    )
    await message.answer(text)


# ═══════════════════════════════════════════════════════════
# 📦 ОБРАБОТКА ЗАКАЗОВ (БЕЗ ИЗМЕНЕНИЙ)
# ═══════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("admin_confirm_"))
async def admin_confirm_order(callback: CallbackQuery, bot: Bot):
    order_id = int(callback.data.split("_")[2])
    order = db.get_order(order_id)

    if not order:
        await callback.answer("❌ Заказ не найден!", show_alert=True)
        return

    if order['status'] not in ('pending', 'paid'):
        await callback.answer(f"⚠️ Уже: {order['status']}", show_alert=True)
        return

    if order.get('invoice_id') is None:
        db.update_order_status(order_id, 'completed')
        safe_name = callback.from_user.full_name.replace("<", "&lt;").replace(">", "&gt;")

        new_text = callback.message.html_text + (
            f"\n\n<blockquote>"
            f"{e('trophy')}{e('check')} <b>ЗАКАЗ ВЫПОЛНЕН</b> {e('check')}{e('trophy')}\n"
            f"{e('sparkle')} Выполнил: {safe_name}"
            f"</blockquote>"
        )
        try:
            await callback.message.edit_text(new_text)
        except Exception:
            pass

        if order['order_type'] == 'stars':
            product_text = f"{e('star')} <b>{order['quantity']} Telegram Звёзд</b>"
        else:
            months_text = {1: "1 месяц", 3: "3 месяца", 6: "6 месяцев", 12: "12 месяцев"}
            product_text = f"{e('crown')} <b>Telegram Премиум — {months_text.get(order['quantity'], str(order['quantity']))}</b>"

        user_text = (
            f"{e('trophy')}{e('sparkle')}{e('diamond')}{e('sparkle')}{e('trophy')}\n"
            f"\n"
            f"{e('check')} <b>ЗАКАЗ #{order_id} ПОДТВЕРЖДЁН И ВЫПОЛНЕН!</b> {e('check')}\n"
            f"\n"
            f"<blockquote>"
            f"{product_text}\n"
            f"{e('gift')} Получатель: @{order['target_username']}\n"
            f"{e('money')} Оплачено: <b>{order['price']:.2f} BYN</b>"
            f"</blockquote>\n"
            f"\n"
            f"<blockquote>"
            f"{e('sparkle')} <b>Спасибо за покупку!</b> {e('sparkle')}\n"
            f"{e('rocket')} <b>Ждём вас снова!</b> {e('rocket')}\n\n"
            f"{e('medal')} Пожалуйста, <b>оставьте отзыв</b> — \n"
            f"это очень важно для нас! {e('heart')}"
            f"</blockquote>\n"
            f"\n"
            f"{e('trophy')}{e('crown')}{e('diamond')}{e('crown')}{e('trophy')}"
        )
        await edit_user_message(bot, order, user_text, after_purchase_keyboard())
        await callback.answer(f"✅ Заказ #{order_id} подтверждён и выполнен!")
    else:
        db.update_order_status(order_id, 'confirmed')
        safe_name = callback.from_user.full_name.replace("<", "&lt;").replace(">", "&gt;")

        new_text = callback.message.html_text + (
            f"\n\n<blockquote>"
            f"{e('check')} <b>СТАТУС:</b> Подтверждён\n"
            f"{e('sparkle')} Админ: {safe_name}"
            f"</blockquote>"
        )
        try:
            await callback.message.edit_text(new_text, reply_markup=admin_order_keyboard(order_id))
        except Exception:
            pass

        user_text = (
            f"{e('check')}{e('sparkle')} <b>Заказ #{order_id} подтверждён!</b>\n"
            f"\n"
            f"<blockquote>"
            f"{e('fire')} Ваш заказ принят в обработку!\n"
            f"{e('lightning')} Ожидайте выполнения.\n\n"
            f"{e('rocket')} <b>Спасибо за доверие!</b>"
            f"</blockquote>"
        )
        await edit_user_message(bot, order, user_text, back_to_menu_keyboard())
        await callback.answer(f"✅ Заказ #{order_id} подтверждён!")


@router.callback_query(F.data.startswith("admin_progress_"))
async def admin_progress_order(callback: CallbackQuery, bot: Bot):
    order_id = int(callback.data.split("_")[2])
    order = db.get_order(order_id)

    if not order:
        await callback.answer("❌ Заказ не найден!", show_alert=True)
        return

    db.update_order_status(order_id, 'in_progress')
    safe_name = callback.from_user.full_name.replace("<", "&lt;").replace(">", "&gt;")

    new_text = callback.message.html_text + (
        f"\n\n<blockquote>"
        f"{e('lightning')} <b>СТАТУС:</b> Выполняется\n"
        f"{e('sparkle')} Админ: {safe_name}"
        f"</blockquote>"
    )
    try:
        await callback.message.edit_text(new_text, reply_markup=admin_order_keyboard(order_id))
    except Exception:
        pass

    user_text = (
        f"{e('lightning')}{e('fire')} <b>Заказ #{order_id} выполняется!</b>\n"
        f"\n"
        f"<blockquote>"
        f"{e('rocket')} Администратор начал выполнение!\n"
        f"{e('sparkle')} Пожалуйста, ожидайте.\n\n"
        f"{e('diamond')} <b>Это не займёт много времени!</b>"
        f"</blockquote>"
    )
    await edit_user_message(bot, order, user_text, back_to_menu_keyboard())
    await callback.answer(f"⚡ Заказ #{order_id} — выполняется!")


@router.callback_query(F.data.startswith("admin_complete_"))
async def admin_complete_order(callback: CallbackQuery, bot: Bot):
    order_id = int(callback.data.split("_")[2])
    order = db.get_order(order_id)

    if not order:
        await callback.answer("❌ Заказ не найден!", show_alert=True)
        return

    db.update_order_status(order_id, 'completed')
    safe_name = callback.from_user.full_name.replace("<", "&lt;").replace(">", "&gt;")

    new_text = callback.message.html_text + (
        f"\n\n<blockquote>"
        f"{e('trophy')}{e('check')} <b>ЗАКАЗ ВЫПОЛНЕН</b> {e('check')}{e('trophy')}\n"
        f"{e('sparkle')} Выполнил: {safe_name}"
        f"</blockquote>"
    )
    try:
        await callback.message.edit_text(new_text)
    except Exception:
        pass

    if order['order_type'] == 'stars':
        product_text = f"{e('star')} <b>{order['quantity']} Telegram Звёзд</b>"
    else:
        months_text = {1: "1 месяц", 3: "3 месяца", 6: "6 месяцев", 12: "12 месяцев"}
        product_text = f"{e('crown')} <b>Telegram Премиум — {months_text.get(order['quantity'], str(order['quantity']))}</b>"

    user_text = (
        f"{e('trophy')}{e('sparkle')}{e('diamond')}{e('sparkle')}{e('trophy')}\n"
        f"\n"
        f"{e('check')} <b>ЗАКАЗ #{order_id} ВЫПОЛНЕН!</b> {e('check')}\n"
        f"\n"
        f"<blockquote>"
        f"{product_text}\n"
        f"{e('gift')} Получатель: @{order['target_username']}\n"
        f"{e('money')} Оплачено: <b>{order['price']:.2f} BYN</b>"
        f"</blockquote>\n"
        f"\n"
        f"<blockquote>"
        f"{e('sparkle')} <b>Спасибо за покупку!</b> {e('sparkle')}\n"
        f"{e('rocket')} <b>Ждём вас снова!</b> {e('rocket')}\n\n"
        f"{e('medal')} Пожалуйста, <b>оставьте отзыв</b> — \n"
        f"это очень важно для нас! {e('heart')}"
        f"</blockquote>\n"
        f"\n"
        f"{e('trophy')}{e('crown')}{e('diamond')}{e('crown')}{e('trophy')}"
    )
    await edit_user_message(bot, order, user_text, after_purchase_keyboard())
    await callback.answer(f"🏆 Заказ #{order_id} выполнен!")


@router.callback_query(F.data.startswith("admin_reject_"))
async def admin_reject_order(callback: CallbackQuery, bot: Bot):
    order_id = int(callback.data.split("_")[2])
    order = db.get_order(order_id)

    if not order:
        await callback.answer("❌ Заказ не найден!", show_alert=True)
        return

    db.update_order_status(order_id, 'rejected')
    safe_name = callback.from_user.full_name.replace("<", "&lt;").replace(">", "&gt;")

    new_text = callback.message.html_text + (
        f"\n\n<blockquote>"
        f"{e('cross')} <b>ЗАКАЗ ОТКЛОНЁН</b> {e('cross')}\n"
        f"{e('sparkle')} Отклонил: {safe_name}"
        f"</blockquote>"
    )
    try:
        await callback.message.edit_text(new_text)
    except Exception:
        pass

    user_text = (
        f"{e('cross')} <b>Заказ #{order_id} отклонён</b>\n"
        f"\n"
        f"<blockquote>"
        f"{e('fire')} К сожалению, ваш заказ отклонён."
        f"</blockquote>\n"
        f"\n"
        f"<blockquote>"
        f"{e('sparkle')} <b>Возможные причины:</b>\n"
        f"• Некорректные данные\n"
        f"• Технические ограничения\n"
        f"• Временная недоступность"
        f"</blockquote>\n"
        f"\n"
        f"<blockquote>"
        f"{e('heart')} Свяжитесь с поддержкой.\n"
        f"{e('rocket')} Или оформите заказ заново."
        f"</blockquote>"
    )
    await edit_user_message(bot, order, user_text, back_to_menu_keyboard())
    await callback.answer(f"❌ Заказ #{order_id} отклонён!")


# ═══════════════════════════════════════════════════════════
# 🔑 ПРОМОКОДЫ
# ═══════════════════════════════════════════════════════════

@router.message(Command("addpromo"))
async def cmd_addpromo(message: Message, state: FSMContext):
    if message.from_user.id not in ADMINS:
        return

    await state.set_state(PromoSetup.waiting_code)
    await message.answer(
        f"{e('sparkle')} <b>Создание промокода</b>\n\n"
        f"Введите уникальный код промокода (латиница, цифры, символ _):"
    )


@router.message(PromoSetup.waiting_code)
async def promo_get_code(message: Message, state: FSMContext):
    code = message.text.strip()
    if not re.match(r'^[a-zA-Z0-9_]+$', code):
        await message.answer("❌ Код может содержать только буквы, цифры и подчёркивание. Попробуйте ещё раз.")
        return
    if db.get_promo(code):
        await message.answer("❌ Такой промокод уже существует. Введите другой.")
        return

    await state.update_data(code=code)
    await state.set_state(PromoSetup.waiting_type)
    await message.answer(
        f"Выберите тип скидки:\n"
        f"Введите <b>percent</b> (процент) или <b>fixed</b> (фиксированная сумма в BYN):"
    )


@router.message(PromoSetup.waiting_type)
async def promo_get_type(message: Message, state: FSMContext):
    type_ = message.text.strip().lower()
    if type_ not in ('percent', 'fixed'):
        await message.answer("❌ Введите 'percent' или 'fixed'.")
        return
    await state.update_data(discount_type=type_)
    await state.set_state(PromoSetup.waiting_value)
    await message.answer("Введите значение скидки (число):\n"
                         "• для percent: например, 10 (означает 10%)\n"
                         "• для fixed: например, 5.5 (означает 5.5 BYN)")


@router.message(PromoSetup.waiting_value)
async def promo_get_value(message: Message, state: FSMContext):
    try:
        value = float(message.text.strip())
        if value <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите положительное число.")
        return
    await state.update_data(discount_value=value)
    await state.set_state(PromoSetup.waiting_expires)
    await message.answer(
        "Введите дату истечения промокода в формате ГГГГ-ММ-ДД ЧЧ:ММ:СС\n"
        "Например: 2025-12-31 23:59:59\n"
        "Или введите 0, если срок не ограничен."
    )


@router.message(PromoSetup.waiting_expires)
async def promo_get_expires(message: Message, state: FSMContext):
    expires = message.text.strip()
    if expires == '0':
        expires = None
    else:
        try:
            from datetime import datetime
            datetime.strptime(expires, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            await message.answer("❌ Неверный формат. Используйте ГГГГ-ММ-ДД ЧЧ:ММ:СС или 0.")
            return

    await state.update_data(expires_at=expires)
    await state.set_state(PromoSetup.waiting_max_uses)
    await message.answer("Введите максимальное количество использований (целое число, например, 10):")


@router.message(PromoSetup.waiting_max_uses)
async def promo_get_max_uses(message: Message, state: FSMContext):
    try:
        max_uses = int(message.text.strip())
        if max_uses <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите целое положительное число.")
        return

    data = await state.get_data()
    code = data['code']
    discount_type = data['discount_type']
    discount_value = data['discount_value']
    expires_at = data.get('expires_at')
    created_by = message.from_user.id

    db.create_promo(code, discount_type, discount_value, expires_at, max_uses, created_by)

    await state.clear()
    await message.answer(
        f"{e('check')} <b>Промокод создан!</b>\n\n"
        f"<blockquote>"
        f"Код: <code>{code}</code>\n"
        f"Тип: {discount_type}\n"
        f"Значение: {discount_value}\n"
        f"Макс. использований: {max_uses}\n"
        f"Истекает: {expires_at or 'никогда'}"
        f"</blockquote>"
    )


@router.message(Command("listpromo"))
async def cmd_listpromo(message: Message):
    if message.from_user.id not in ADMINS:
        return

    promos = db.list_promos()
    if not promos:
        await message.answer("📭 Нет созданных промокодов.")
        return

    text = f"{e('sparkle')} <b>Список промокодов</b>\n\n"
    for promo in promos:
        status = "✅ активен" if promo['is_active'] else "❌ неактивен"
        text += (
            f"<blockquote>"
            f"<b>{promo['code']}</b>\n"
            f"Скидка: {promo['discount_value']} ({promo['discount_type']})\n"
            f"Использовано: {promo['used_count']}/{promo['max_uses']}\n"
            f"Статус: {status}\n"
            f"Истекает: {promo['expires_at'] or 'никогда'}"
            f"</blockquote>\n"
        )
    await message.answer(text)


@router.message(Command("delpromo"))
async def cmd_delpromo(message: Message):
    if message.from_user.id not in ADMINS:
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("❌ Укажите код промокода: /delpromo КОД")
        return

    code = args[1].strip()
    promo = db.get_promo(code)
    if not promo:
        await message.answer(f"❌ Промокод <code>{code}</code> не найден.")
        return

    db.delete_promo(code)
    await message.answer(f"✅ Промокод <code>{code}</code> удалён.")