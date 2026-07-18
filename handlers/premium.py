# handlers/premium.py

import asyncio
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from keyboards import (premium_target_keyboard, premium_duration_keyboard,
                       payment_method_keyboard, payment_link_keyboard,
                       back_to_menu_keyboard, admin_order_keyboard,
                       after_purchase_keyboard, byn_payment_keyboard,
                       promo_skip_keyboard)
from config import PREMIUM_PRICES, ADMIN_GROUP_ID, BYN_TO_USD, BANK_CARD_NUMBER, BANK_CARD_HOLDER, BANK_NAME, REMINDER_DELAY_SECONDS, REFERRAL_BONUS_PERCENT
from emoji_manager import e
from database import Database
from crypto_pay import create_invoice
from utils import edit_menu, edit_menu_by_id, remind_about_payment

router = Router()
db = Database()


class PremiumOrder(StatesGroup):
    waiting_target_username = State()
    waiting_duration = State()
    choosing_payment = State()
    waiting_payment = State()
    waiting_byn_payment = State()
    waiting_promo = State()


@router.callback_query(F.data == "buy_premium")
async def buy_premium_start(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.update_data(main_message_id=callback.message.message_id)

    text = (
        f"{e('crown')}{e('sparkle')} <b>Покупка Telegram Премиум</b> {e('sparkle')}{e('crown')}\n\n"
        f"<blockquote>"
        f"{e('diamond')} <b>Без захода в аккаунт!</b>\n"
        f"{e('fire')} Выдаётся <b>подарочная карта</b>"
        f"</blockquote>\n\n"
        f"{e('money')} <b>Цены:</b>\n"
        f"<blockquote>"
        f"{e('lightning')} 1 месяц — <b>{PREMIUM_PRICES[1]:.0f} BYN</b>\n"
        f"{e('fire')} 3 месяца — <b>{PREMIUM_PRICES[3]:.0f} BYN</b>\n"
        f"{e('trophy')} 6 месяцев — <b>{PREMIUM_PRICES[6]:.0f} BYN</b>\n"
        f"{e('crown')} 12 месяцев — <b>{PREMIUM_PRICES[12]:.0f} BYN</b>"
        f"</blockquote>\n\n"
        f"{e('gift')} <b>Кому вы хотите приобрести Премиум?</b>"
    )
    await edit_menu(callback, text, premium_target_keyboard())
    await callback.answer()


@router.callback_query(F.data == "premium_target_self")
async def premium_target_self(callback: CallbackQuery, state: FSMContext):
    user = callback.from_user
    username = user.username

    if not username:
        await edit_menu(callback,
            f"{e('cross')} <b>Ошибка!</b>\n\n"
            f"<blockquote>У вас не установлен username.</blockquote>",
            back_to_menu_keyboard()
        )
        await callback.answer()
        return

    await state.update_data(
        target_type="self", target_username=username,
        main_message_id=callback.message.message_id
    )

    text = (
        f"{e('crown')} <b>Премиум для себя</b>\n\n"
        f"<blockquote>{e('gift')} Получатель: <b>@{username}</b></blockquote>\n\n"
        f"{e('fire')} <b>Выберите срок подписки:</b>"
    )
    await edit_menu(callback, text, premium_duration_keyboard())
    await state.set_state(PremiumOrder.waiting_duration)
    await callback.answer()


@router.callback_query(F.data == "premium_target_other")
async def premium_target_other(callback: CallbackQuery, state: FSMContext):
    await state.update_data(target_type="other", main_message_id=callback.message.message_id)

    text = (
        f"{e('fire')} <b>Премиум для другого</b>\n\n"
        f"{e('gift')} Введите <b>username</b> получателя (без @):\n\n"
        f"<blockquote>{e('lightning')} Например: <code>username123</code></blockquote>"
    )
    await edit_menu(callback, text, back_to_menu_keyboard())
    await state.set_state(PremiumOrder.waiting_target_username)
    await callback.answer()


@router.message(PremiumOrder.waiting_target_username)
async def premium_get_target(message: Message, state: FSMContext, bot: Bot):
    username = message.text.strip()
    data = await state.get_data()
    main_msg_id = data.get('main_message_id')
    chat_id = message.chat.id

    try:
        await message.delete()
    except Exception:
        pass

    # Проверка на наличие @
    if username.startswith('@'):
        new_id = await edit_menu_by_id(bot, chat_id, main_msg_id,
            f"{e('cross')} <b>Ошибка!</b>\n\n"
            f"<blockquote>Введите username <b>без</b> символа @!\n\n"
            f"Попробуйте ещё раз:</blockquote>",
            back_to_menu_keyboard()
        )
        await state.update_data(main_message_id=new_id)
        return

    username = username.lstrip('@')

    if not username or len(username) < 3:
        new_id = await edit_menu_by_id(bot, chat_id, main_msg_id,
            f"{e('cross')} <b>Неверный username!</b>\n\n"
            f"<blockquote>Введите корректный username:</blockquote>",
            back_to_menu_keyboard()
        )
        await state.update_data(main_message_id=new_id)
        return

    await state.update_data(target_username=username)
    text = (
        f"{e('crown')} <b>Премиум для @{username}</b>\n\n"
        f"{e('fire')} <b>Выберите срок подписки:</b>"
    )
    new_id = await edit_menu_by_id(bot, chat_id, main_msg_id, text, premium_duration_keyboard())
    await state.update_data(main_message_id=new_id)
    await state.set_state(PremiumOrder.waiting_duration)


@router.callback_query(F.data.startswith("premium_months_"), PremiumOrder.waiting_duration)
async def premium_select_duration(callback: CallbackQuery, state: FSMContext):
    months = int(callback.data.split("_")[2])
    price = PREMIUM_PRICES[months]
    data = await state.get_data()
    target_username = data.get("target_username", "")
    target_type = data.get("target_type", "self")
    await state.update_data(months=months, price=price, original_price=price)

    months_text = {1: "1 месяц", 3: "3 месяца", 6: "6 месяцев", 12: "12 месяцев"}
    target_text = "Себе" if target_type == "self" else "Другому"
    price_usd = round(price * BYN_TO_USD, 2)

    text = (
        f"{e('sparkle')}{e('diamond')} <b>Подтверждение заказа</b> {e('diamond')}{e('sparkle')}\n\n"
        f"<blockquote>"
        f"{e('crown')} <b>Товар:</b> Telegram Премиум\n"
        f"{e('fire')} <b>Срок:</b> {months_text[months]}\n"
        f"{e('gift')} <b>Кому:</b> {target_text} (@{target_username})\n"
        f"{e('diamond')} <b>Способ:</b> Подарочная карта\n"
        f"{e('money')} <b>Цена:</b> {price:.2f} BYN (~{price_usd}$)"
        f"</blockquote>\n\n"
        f"{e('check')} <b>Введите промокод или пропустите:</b>"
    )
    await edit_menu(callback, text, promo_skip_keyboard())
    await state.set_state(PremiumOrder.waiting_promo)
    await callback.answer()


# --- ПРОМОКОД ---
@router.message(PremiumOrder.waiting_promo)
async def process_promo_premium(message: Message, state: FSMContext, bot: Bot):
    code = message.text.strip()
    data = await state.get_data()
    main_msg_id = data.get('main_message_id')
    chat_id = message.chat.id
    original_price = data.get('original_price', data['price'])

    try:
        await message.delete()
    except Exception:
        pass

    promo = db.get_promo(code)
    if promo and promo['is_active'] and promo['used_count'] < promo['max_uses']:
        discount = promo['discount_value']
        new_price = original_price
        if promo['discount_type'] == 'percent':
            new_price = original_price * (1 - discount / 100)
        else:
            new_price = max(0, original_price - discount)

        await state.update_data(
            price=round(new_price, 2),
            promocode_id=promo['id'],
            discount_amount=round(original_price - new_price, 2)
        )
        db.use_promo(code)
        text = (
            f"{e('check')} <b>Промокод применён!</b>\n\n"
            f"<blockquote>"
            f"{e('money')} <b>Цена со скидкой:</b> {new_price:.2f} BYN\n"
            f"{e('diamond')} <b>Экономия:</b> {original_price - new_price:.2f} BYN"
            f"</blockquote>\n\n"
            f"{e('check')} <b>Выберите способ оплаты:</b>"
        )
        await edit_menu_by_id(bot, chat_id, main_msg_id, text, payment_method_keyboard())
        await state.set_state(PremiumOrder.choosing_payment)
    else:
        text = (
            f"{e('cross')} <b>Неверный или неактивный промокод!</b>\n\n"
            f"<blockquote>"
            f"Попробуйте ещё раз или нажмите <b>«Пропустить»</b>."
            f"</blockquote>"
        )
        new_id = await edit_menu_by_id(bot, chat_id, main_msg_id, text, promo_skip_keyboard())
        await state.update_data(main_message_id=new_id)


@router.callback_query(F.data == "skip_promo", PremiumOrder.waiting_promo)
async def skip_promo_premium(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if 'original_price' in data:
        await state.update_data(price=data['original_price'], promocode_id=None, discount_amount=0)

    months_text = {1: "1 месяц", 3: "3 месяца", 6: "6 месяцев", 12: "12 месяцев"}
    target_text = "Себе" if data['target_type'] == "self" else "Другому"
    text = (
        f"{e('sparkle')}{e('diamond')} <b>Подтверждение заказа</b> {e('diamond')}{e('sparkle')}\n\n"
        f"<blockquote>"
        f"{e('crown')} <b>Товар:</b> Telegram Премиум\n"
        f"{e('fire')} <b>Срок:</b> {months_text[data['months']]}\n"
        f"{e('gift')} <b>Кому:</b> {target_text} (@{data['target_username']})\n"
        f"{e('diamond')} <b>Способ:</b> Подарочная карта\n"
        f"{e('money')} <b>Цена:</b> {data['price']:.2f} BYN"
        f"</blockquote>\n\n"
        f"{e('check')} <b>Выберите способ оплаты:</b>"
    )
    await edit_menu(callback, text, payment_method_keyboard())
    await state.set_state(PremiumOrder.choosing_payment)
    await callback.answer()


# --- ОПЛАТА BYN ---
@router.callback_query(F.data == "pay_byn", PremiumOrder.choosing_payment)
async def pay_byn_premium(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    user = callback.from_user
    months_text = {1: "1 месяц", 3: "3 месяца", 6: "6 месяцев", 12: "12 месяцев"}

    order_id = db.create_order(
        user_id=user.id, username=user.username or "",
        full_name=user.full_name, order_type="premium",
        quantity=data['months'], target_username=data['target_username'],
        target_type=data['target_type'], price=data['price'],
        promocode_id=data.get('promocode_id'),
        discount_amount=data.get('discount_amount', 0)
    )

    await state.update_data(order_id=order_id)

    text = (
        f"{e('money')}{e('sparkle')} <b>Оплата заказа #{order_id} (BYN)</b> {e('sparkle')}{e('money')}\n\n"
        f"<blockquote>"
        f"{e('crown')} <b>Товар:</b> Telegram Премиум — {months_text[data['months']]}\n"
        f"{e('gift')} <b>Кому:</b> @{data['target_username']}\n"
        f"{e('money')} <b>Сумма:</b> {data['price']:.2f} BYN"
        f"</blockquote>\n\n"
        f"<blockquote>"
        f"{e('diamond')} <b>Реквизиты для перевода:</b>\n"
        f"Карта: <b>{BANK_CARD_NUMBER}</b>\n"
        f"Получатель: <b>{BANK_CARD_HOLDER}</b>\n"
        f"Банк: <b>{BANK_NAME}</b>\n"
        f"{e('lightning')} <b>В назначении платежа укажите номер заказа #{order_id}</b>"
        f"</blockquote>\n\n"
        f"<blockquote>"
        f"{e('fire')} После перевода нажмите <b>«Я оплатил»</b>.\n"
        f"{e('rocket')} Администратор проверит поступление и выполнит заказ."
        f"</blockquote>"
    )
    await edit_menu(callback, text, byn_payment_keyboard(order_id))
    db.set_user_message_id(order_id, callback.message.message_id, callback.message.chat.id)
    await state.set_state(PremiumOrder.waiting_byn_payment)
    await callback.answer()

    asyncio.create_task(remind_about_payment(order_id, user.id, bot, REMINDER_DELAY_SECONDS))


@router.callback_query(F.data.startswith("byn_paid_"), PremiumOrder.waiting_byn_payment)
async def byn_paid_premium(callback: CallbackQuery, state: FSMContext, bot: Bot):
    order_id = int(callback.data.split("_")[2])
    order = db.get_order(order_id)

    if not order:
        await callback.answer("❌ Заказ не найден!", show_alert=True)
        return

    if order.get('payment_status') == 'paid':
        await callback.answer("✅ Уже оплачено!", show_alert=True)
        return

    db.update_payment_status(order_id, 'paid')
    db.update_order_status(order_id, 'paid')

    safe_name = callback.from_user.full_name.replace("<", "&lt;").replace(">", "&gt;")
    target_text = "Себе" if order['target_type'] == "self" else "Другому"
    months_text = {1: "1 месяц", 3: "3 месяца", 6: "6 месяцев", 12: "12 месяцев"}

    user_text = (
        f"{e('clock')}{e('sparkle')} <b>Платёж отправлен на проверку!</b> {e('sparkle')}{e('clock')}\n\n"
        f"<blockquote>"
        f"{e('lightning')} Ваш заказ #{order_id} передан на проверку.\n"
        f"{e('fire')} Администратор проверит поступление средств.\n\n"
        f"{e('rocket')} Пожалуйста, ожидайте подтверждения."
        f"</blockquote>"
    )
    await edit_menu(callback, user_text, back_to_menu_keyboard())

    admin_text = (
        f"{e('lightning')}{e('fire')} <b>НОВЫЙ ОПЛАЧЕННЫЙ ЗАКАЗ #{order_id}</b> {e('fire')}{e('lightning')}\n\n"
        f"<blockquote>"
        f"{e('crown')} <b>Тип:</b> Telegram Премиум\n"
        f"{e('diamond')} <b>Срок:</b> {months_text[order['quantity']]}\n"
        f"{e('money')} <b>Цена:</b> {order['price']:.2f} BYN\n"
        f"{e('check')} <b>Оплата:</b> BYN (ожидает подтверждения)"
        f"</blockquote>\n\n"
        f"<blockquote>"
        f"{e('gift')} <b>Кому:</b> {target_text}\n"
        f"{e('fire')} <b>Получатель:</b> @{order['target_username']}"
        f"</blockquote>\n\n"
        f"<blockquote>"
        f"{e('crown')} <b>Покупатель:</b> {safe_name}\n"
        f"{e('sparkle')} <b>Username:</b> @{order.get('username') or 'Нет'}\n"
        f"{e('lightning')} <b>User ID:</b> <code>{order['user_id']}</code>"
        f"</blockquote>\n\n"
        f"{e('rocket')} <b>Статус:</b> Оплачено, ожидает подтверждения"
    )
    admin_msg = await bot.send_message(
        chat_id=ADMIN_GROUP_ID, text=admin_text,
        reply_markup=admin_order_keyboard(order_id)
    )
    db.set_admin_message_id(order_id, admin_msg.message_id)

    # Бонус рефереру
    user_data = db.get_user(order['user_id'])
    if user_data and user_data.get('referred_by'):
        referrer_id = user_data['referred_by']
        ref = db.get_referral(referrer_id, order['user_id'])
        if ref and not ref['is_rewarded']:
            bonus = order['price'] * REFERRAL_BONUS_PERCENT / 100
            bonus_stars = int(bonus * 20)
            if bonus_stars > 0:
                db.add_balance_stars(referrer_id, bonus_stars)
                db.mark_referral_rewarded(ref['id'], bonus_stars, REFERRAL_BONUS_PERCENT)
                try:
                    await bot.send_message(
                        referrer_id,
                        f"{e('gift_box')} <b>Ваш друг #{order['user_id']} совершил первую покупку!</b>\n"
                        f"<blockquote>"
                        f"{e('star')} Вам начислено <b>{bonus_stars} звёзд</b> (5% от суммы заказа)!\n"
                        f"{e('rocket')} Приглашайте ещё друзей и получайте бонусы!"
                        f"</blockquote>"
                    )
                except Exception:
                    pass

    await state.clear()
    await callback.answer("✅ Платёж отправлен на проверку", show_alert=True)


# --- ОПЛАТА CRYPTO ---
@router.callback_query(F.data == "pay_crypto", PremiumOrder.choosing_payment)
async def pay_crypto_premium(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    user = callback.from_user
    months_text = {1: "1 месяц", 3: "3 месяца", 6: "6 месяцев", 12: "12 месяцев"}

    order_id = db.create_order(
        user_id=user.id, username=user.username or "",
        full_name=user.full_name, order_type="premium",
        quantity=data['months'], target_username=data['target_username'],
        target_type=data['target_type'], price=data['price'],
        promocode_id=data.get('promocode_id'),
        discount_amount=data.get('discount_amount', 0)
    )

    description = f"Telegram Premium {months_text[data['months']]}"
    invoice = await create_invoice(data['price'], order_id, description)

    if not invoice['success']:
        await edit_menu(callback,
            f"{e('cross')} <b>Ошибка создания платежа!</b>\n\n"
            f"<blockquote>{invoice['error']}</blockquote>",
            back_to_menu_keyboard()
        )
        await state.clear()
        await callback.answer()
        return

    db.update_payment(order_id, invoice['invoice_id'], invoice['pay_url'], invoice['amount_usd'])
    target_text = "Себе" if data['target_type'] == "self" else "Другому"

    text = (
        f"{e('money')}{e('sparkle')} <b>Оплата заказа #{order_id}</b> {e('sparkle')}{e('money')}\n\n"
        f"<blockquote>"
        f"{e('crown')} <b>Товар:</b> Telegram Премиум — {months_text[data['months']]}\n"
        f"{e('gift')} <b>Кому:</b> {target_text} (@{data['target_username']})"
        f"</blockquote>\n\n"
        f"<blockquote>"
        f"{e('money')} <b>Сумма:</b> {data['price']:.2f} BYN\n"
        f"{e('diamond')} <b>К оплате:</b> ~{invoice['amount_usd']}$ (USDT/TON/BTC)"
        f"</blockquote>\n\n"
        f"<blockquote>"
        f"{e('lightning')} Нажмите <b>«Оплатить»</b>\n"
        f"{e('fire')} После оплаты — <b>«Проверить оплату»</b>"
        f"</blockquote>"
    )
    await edit_menu(callback, text, payment_link_keyboard(invoice['pay_url'], order_id))
    db.set_user_message_id(order_id, callback.message.message_id, callback.message.chat.id)
    await state.update_data(order_id=order_id, invoice_id=invoice['invoice_id'])
    await state.set_state(PremiumOrder.waiting_payment)
    await callback.answer()


@router.callback_query(F.data == "cancel_order")
async def cancel_order(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    text = (
        f"{e('cross')} <b>Заказ отменён</b>\n\n"
        f"<blockquote>{e('rocket')} Вы можете вернуться в главное меню.</blockquote>"
    )
    await edit_menu(callback, text, back_to_menu_keyboard())
    await callback.answer("Заказ отменён")