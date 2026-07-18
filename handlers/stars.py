# handlers/stars.py

import asyncio
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from keyboards import (stars_target_keyboard, stars_packs_keyboard,
                       payment_method_keyboard, payment_link_keyboard,
                       back_to_menu_keyboard, admin_order_keyboard,
                       after_purchase_keyboard, byn_payment_keyboard,
                       promo_skip_keyboard)
from config import STARS_PRICE_PER_ONE, MIN_STARS, ADMIN_GROUP_ID, BYN_TO_USD, BANK_CARD_NUMBER, BANK_CARD_HOLDER, BANK_NAME, REMINDER_DELAY_SECONDS, REFERRAL_BONUS_PERCENT
from emoji_manager import e
from database import Database
from crypto_pay import create_invoice, check_invoice
from utils import edit_menu, edit_menu_by_id, remind_about_payment

router = Router()
db = Database()


class StarsOrder(StatesGroup):
    waiting_target_username = State()
    waiting_custom_quantity = State()
    choosing_payment = State()
    waiting_payment = State()
    waiting_byn_payment = State()
    waiting_promo = State()


@router.callback_query(F.data == "buy_stars")
async def buy_stars_start(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.update_data(main_message_id=callback.message.message_id)

    text = (
        f"{e('star')}{e('sparkle')} <b>Покупка Telegram Звёзд</b> {e('sparkle')}{e('star')}\n\n"
        f"<blockquote>"
        f"{e('diamond')} Минимальный заказ: <b>{MIN_STARS} звёзд</b>\n"
        f"{e('money')} Цена: <b>50 звёзд = 2.6 BYN</b>"
        f"</blockquote>\n\n"
        f"{e('gift')} <b>Кому вы хотите приобрести звёзды?</b>"
    )
    await edit_menu(callback, text, stars_target_keyboard())
    await callback.answer()


@router.callback_query(F.data == "stars_target_self")
async def stars_target_self(callback: CallbackQuery, state: FSMContext):
    user = callback.from_user
    username = user.username

    if not username:
        await edit_menu(callback,
            f"{e('cross')} <b>Ошибка!</b>\n\n"
            f"<blockquote>У вас не установлен <b>username</b>.</blockquote>",
            back_to_menu_keyboard()
        )
        await callback.answer()
        return

    await state.update_data(
        target_type="self", target_username=username,
        main_message_id=callback.message.message_id
    )

    text = (
        f"{e('star')} <b>Покупка звёзд для себя</b>\n\n"
        f"<blockquote>{e('gift')} Получатель: <b>@{username}</b></blockquote>\n\n"
        f"{e('fire')} <b>Выберите пакет или введите своё количество:</b>"
    )
    await edit_menu(callback, text, stars_packs_keyboard())
    await callback.answer()


@router.callback_query(F.data == "stars_target_other")
async def stars_target_other(callback: CallbackQuery, state: FSMContext):
    await state.update_data(target_type="other", main_message_id=callback.message.message_id)

    text = (
        f"{e('fire')} <b>Покупка звёзд для другого</b>\n\n"
        f"{e('gift')} Введите <b>username</b> получателя (без @):\n\n"
        f"<blockquote>{e('lightning')} Например: <code>username123</code></blockquote>"
    )
    await edit_menu(callback, text, back_to_menu_keyboard())
    await state.set_state(StarsOrder.waiting_target_username)
    await callback.answer()


@router.message(StarsOrder.waiting_target_username)
async def stars_get_target_username(message: Message, state: FSMContext, bot: Bot):
    username = message.text.strip()
    data = await state.get_data()
    main_msg_id = data.get('main_message_id')
    chat_id = message.chat.id

    # Удаляем сообщение пользователя
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

    # Убираем @, если он есть (на всякий случай)
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
        f"{e('star')} <b>Покупка звёзд для @{username}</b>\n\n"
        f"{e('fire')} <b>Выберите пакет или введите своё количество:</b>"
    )
    new_id = await edit_menu_by_id(bot, chat_id, main_msg_id, text, stars_packs_keyboard())
    await state.update_data(main_message_id=new_id)
    await state.set_state(None)


@router.callback_query(F.data.startswith("stars_pack_"))
async def stars_select_pack(callback: CallbackQuery, state: FSMContext):
    quantity = int(callback.data.split("_")[2])
    price = quantity * STARS_PRICE_PER_ONE
    data = await state.get_data()
    target_username = data.get("target_username", "")
    target_type = data.get("target_type", "self")

    await state.update_data(quantity=quantity, price=price, original_price=price)
    target_text = "Себе" if target_type == "self" else "Другому"
    price_usd = round(price * BYN_TO_USD, 2)

    text = (
        f"{e('sparkle')}{e('diamond')} <b>Подтверждение заказа</b> {e('diamond')}{e('sparkle')}\n\n"
        f"<blockquote>"
        f"{e('star')} <b>Товар:</b> Telegram Звёзды\n"
        f"{e('fire')} <b>Количество:</b> {quantity} шт.\n"
        f"{e('gift')} <b>Кому:</b> {target_text} (@{target_username})\n"
        f"{e('money')} <b>Цена:</b> {price:.2f} BYN (~{price_usd}$)"
        f"</blockquote>\n\n"
        f"{e('check')} <b>Введите промокод или пропустите:</b>"
    )
    await edit_menu(callback, text, promo_skip_keyboard())
    await state.set_state(StarsOrder.waiting_promo)
    await callback.answer()


@router.callback_query(F.data == "stars_custom")
async def stars_custom(callback: CallbackQuery, state: FSMContext):
    text = (
        f"{e('star')} <b>Своё количество звёзд</b>\n\n"
        f"<blockquote>"
        f"{e('fire')} Введите количество (минимум {MIN_STARS}):\n"
        f"{e('lightning')} Любое число: 55, 77, 123, 456..."
        f"</blockquote>"
    )
    await edit_menu(callback, text, back_to_menu_keyboard())
    await state.set_state(StarsOrder.waiting_custom_quantity)
    await callback.answer()


@router.message(StarsOrder.waiting_custom_quantity)
async def stars_get_custom_quantity(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    main_msg_id = data.get('main_message_id')
    chat_id = message.chat.id

    try:
        await message.delete()
    except Exception:
        pass

    try:
        quantity = int(message.text.strip())
    except ValueError:
        new_id = await edit_menu_by_id(bot, chat_id, main_msg_id,
            f"{e('cross')} <b>Ошибка!</b>\n\n"
            f"<blockquote>Введите <b>целое число</b> от {MIN_STARS}:</blockquote>",
            back_to_menu_keyboard()
        )
        await state.update_data(main_message_id=new_id)
        return

    if quantity < MIN_STARS:
        new_id = await edit_menu_by_id(bot, chat_id, main_msg_id,
            f"{e('cross')} <b>Минимум {MIN_STARS} звёзд!</b>\n\n"
            f"<blockquote>Вы ввели: {quantity}. Попробуйте ещё раз:</blockquote>",
            back_to_menu_keyboard()
        )
        await state.update_data(main_message_id=new_id)
        return

    price = quantity * STARS_PRICE_PER_ONE
    target_username = data.get("target_username", "")
    target_type = data.get("target_type", "self")
    target_text = "Себе" if target_type == "self" else "Другому"
    price_usd = round(price * BYN_TO_USD, 2)

    await state.update_data(quantity=quantity, price=price, original_price=price)

    text = (
        f"{e('sparkle')}{e('diamond')} <b>Подтверждение заказа</b> {e('diamond')}{e('sparkle')}\n\n"
        f"<blockquote>"
        f"{e('star')} <b>Товар:</b> Telegram Звёзды\n"
        f"{e('fire')} <b>Количество:</b> {quantity} шт.\n"
        f"{e('gift')} <b>Кому:</b> {target_text} (@{target_username})\n"
        f"{e('money')} <b>Цена:</b> {price:.2f} BYN (~{price_usd}$)"
        f"</blockquote>\n\n"
        f"{e('check')} <b>Введите промокод или пропустите:</b>"
    )
    new_id = await edit_menu_by_id(bot, chat_id, main_msg_id, text, promo_skip_keyboard())
    await state.update_data(main_message_id=new_id)
    await state.set_state(StarsOrder.waiting_promo)


# --- ОБРАБОТКА ПРОМОКОДА ---
@router.message(StarsOrder.waiting_promo)
async def process_promo_code(message: Message, state: FSMContext, bot: Bot):
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
        else:  # fixed
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
        await state.set_state(StarsOrder.choosing_payment)
    else:
        text = (
            f"{e('cross')} <b>Неверный или неактивный промокод!</b>\n\n"
            f"<blockquote>"
            f"Попробуйте ещё раз или нажмите <b>«Пропустить»</b>."
            f"</blockquote>"
        )
        new_id = await edit_menu_by_id(bot, chat_id, main_msg_id, text, promo_skip_keyboard())
        await state.update_data(main_message_id=new_id)


@router.callback_query(F.data == "skip_promo", StarsOrder.waiting_promo)
async def skip_promo_callback(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if 'original_price' in data:
        await state.update_data(price=data['original_price'], promocode_id=None, discount_amount=0)
    text = (
        f"{e('sparkle')}{e('diamond')} <b>Подтверждение заказа</b> {e('diamond')}{e('sparkle')}\n\n"
        f"<blockquote>"
        f"{e('star')} <b>Товар:</b> Telegram Звёзды\n"
        f"{e('fire')} <b>Количество:</b> {data['quantity']} шт.\n"
        f"{e('gift')} <b>Кому:</b> {'Себе' if data['target_type'] == 'self' else 'Другому'} (@{data['target_username']})\n"
        f"{e('money')} <b>Цена:</b> {data['price']:.2f} BYN"
        f"</blockquote>\n\n"
        f"{e('check')} <b>Выберите способ оплаты:</b>"
    )
    await edit_menu(callback, text, payment_method_keyboard())
    await state.set_state(StarsOrder.choosing_payment)
    await callback.answer()


# --- ОПЛАТА BYN ---
@router.callback_query(F.data == "pay_byn", StarsOrder.choosing_payment)
async def pay_byn_stars(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    user = callback.from_user

    order_id = db.create_order(
        user_id=user.id, username=user.username or "",
        full_name=user.full_name, order_type="stars",
        quantity=data['quantity'], target_username=data['target_username'],
        target_type=data['target_type'], price=data['price'],
        promocode_id=data.get('promocode_id'),
        discount_amount=data.get('discount_amount', 0)
    )

    await state.update_data(order_id=order_id)

    text = (
        f"{e('money')}{e('sparkle')} <b>Оплата заказа #{order_id} (BYN)</b> {e('sparkle')}{e('money')}\n\n"
        f"<blockquote>"
        f"{e('star')} <b>Товар:</b> {data['quantity']} Telegram Звёзд\n"
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
    await state.set_state(StarsOrder.waiting_byn_payment)
    await callback.answer()

    asyncio.create_task(remind_about_payment(order_id, user.id, bot, REMINDER_DELAY_SECONDS))


@router.callback_query(F.data.startswith("byn_paid_"), StarsOrder.waiting_byn_payment)
async def byn_paid_stars(callback: CallbackQuery, state: FSMContext, bot: Bot):
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
        f"{e('star')} <b>Тип:</b> Telegram Звёзды\n"
        f"{e('diamond')} <b>Количество:</b> {order['quantity']} шт.\n"
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
@router.callback_query(F.data == "pay_crypto", StarsOrder.choosing_payment)
async def pay_crypto_stars(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    user = callback.from_user

    order_id = db.create_order(
        user_id=user.id, username=user.username or "",
        full_name=user.full_name, order_type="stars",
        quantity=data['quantity'], target_username=data['target_username'],
        target_type=data['target_type'], price=data['price'],
        promocode_id=data.get('promocode_id'),
        discount_amount=data.get('discount_amount', 0)
    )

    description = f"Telegram Звёзды x{data['quantity']}"
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
        f"{e('star')} <b>Товар:</b> {data['quantity']} Telegram Звёзд\n"
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
    await state.set_state(StarsOrder.waiting_payment)
    await callback.answer()


@router.callback_query(F.data.startswith("check_payment_"))
async def check_payment(callback: CallbackQuery, state: FSMContext, bot: Bot):
    order_id = int(callback.data.split("_")[2])
    order = db.get_order(order_id)

    if not order:
        await callback.answer("❌ Заказ не найден!", show_alert=True)
        return

    if order.get('payment_status') == 'paid':
        await callback.answer("✅ Уже оплачено!", show_alert=True)
        return

    invoice_id = order.get('invoice_id')
    if not invoice_id:
        await callback.answer("❌ Платёж не найден!", show_alert=True)
        return

    result = await check_invoice(invoice_id)

    if not result['success']:
        await callback.answer(f"❌ Ошибка: {result['error']}", show_alert=True)
        return

    if result['paid']:
        db.update_payment_status(order_id, 'paid')
        db.update_order_status(order_id, 'paid')

        safe_name = callback.from_user.full_name.replace("<", "&lt;").replace(">", "&gt;")
        target_text = "Себе" if order['target_type'] == "self" else "Другому"

        user_text = (
            f"{e('check')}{e('sparkle')} <b>Оплата получена!</b> {e('sparkle')}{e('check')}\n\n"
            f"<blockquote>"
            f"{e('star')} <b>Заказ #{order_id}</b>\n"
            f"{e('diamond')} {order['quantity']} Telegram Звёзд\n"
            f"{e('gift')} Кому: {target_text} (@{order['target_username']})\n"
            f"{e('money')} Оплачено: <b>{order['price']:.2f} BYN</b>"
            f"</blockquote>\n\n"
            f"<blockquote>"
            f"{e('lightning')} Заказ передан администратору!\n"
            f"{e('fire')} Ожидайте выполнения.\n\n"
            f"{e('rocket')} <b>Спасибо за покупку!</b>"
            f"</blockquote>"
        )
        await edit_menu(callback, user_text, after_purchase_keyboard())

        admin_text = (
            f"{e('lightning')}{e('fire')} <b>НОВЫЙ ОПЛАЧЕННЫЙ ЗАКАЗ #{order_id}</b> {e('fire')}{e('lightning')}\n\n"
            f"<blockquote>"
            f"{e('star')} <b>Тип:</b> Telegram Звёзды\n"
            f"{e('diamond')} <b>Количество:</b> {order['quantity']} шт.\n"
            f"{e('money')} <b>Цена:</b> {order['price']:.2f} BYN (~{order.get('price_usd', 0)}$)\n"
            f"{e('check')} <b>Оплата:</b> CryptoBot ✅"
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
            f"{e('rocket')} <b>Статус:</b> Оплачено, ожидает выполнения"
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
        await callback.answer("✅ Оплата подтверждена!", show_alert=True)
    else:
        await callback.answer("⏳ Оплата ещё не поступила. Попробуйте позже.", show_alert=True)


@router.callback_query(F.data == "cancel_order")
async def cancel_order(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    text = (
        f"{e('cross')} <b>Заказ отменён</b>\n\n"
        f"<blockquote>{e('rocket')} Вы можете вернуться в главное меню.</blockquote>"
    )
    await edit_menu(callback, text, back_to_menu_keyboard())
    await callback.answer("Заказ отменён")