# handlers/start.py

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

from keyboards import main_menu_keyboard, back_to_menu_keyboard, assortment_keyboard, referral_info_keyboard
from config import PREMIUM_PRICES, STARS_PRICE_PER_ONE, MIN_STARS, REFERRAL_BONUS_STARS, BOT_USERNAME
from emoji_manager import e
from database import Database
from utils import send_menu, edit_menu

router = Router()
db = Database()


def get_welcome_text(full_name: str, referral_code: str = None) -> str:
    safe_name = full_name.replace("<", "&lt;").replace(">", "&gt;")
    text = (
        f"{e('sparkle')}{e('diamond')}{e('sparkle')} <b>Добро пожаловать!</b> {e('sparkle')}{e('diamond')}{e('sparkle')}\n"
        f"\n"
        f"<blockquote>"
        f"{e('fire')} Привет, <b>{safe_name}</b>!\n\n"
        f"{e('rocket')} Это официальный магазин <b>TG Звёзд и Премиума!</b>\n\n"
        f"{e('star')} <b>Telegram Звёзды</b> — от {MIN_STARS} шт.\n"
        f"{e('crown')} <b>Telegram Премиум</b> — от {PREMIUM_PRICES[1]:.0f} BYN"
        f"</blockquote>\n"
        f"\n"
        f"<blockquote>"
        f"{e('lightning')} <b>Быстрая выдача</b> {e('lightning')}\n"
        f"{e('trophy')} <b>Лучшие цены</b> {e('trophy')}\n"
        f"{e('heart')} <b>Гарантия качества</b> {e('heart')}"
        f"</blockquote>\n"
        f"\n"
        f"{e('gift')} <b>Выберите что хотите приобрести:</b>"
    )
    if referral_code:
        text += f"\n\n{e('gift_box')} <b>Ваш реферальный код:</b> <code>{referral_code}</code>\n"
        text += f"{e('rocket')} Приглашайте друзей и получайте бонусы!"
    return text


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = message.from_user
    args = message.text.split()

    referred_by = None
    if len(args) > 1 and args[1].startswith('ref_'):
        ref_code = args[1][4:]  # убираем 'ref_'
        referrer = db.get_user_by_ref_code(ref_code)
        if referrer and referrer['user_id'] != user.id:
            referred_by = referrer['user_id']
            db.save_referral(referrer['user_id'], user.id)

    referral_code = db.add_user(user.id, user.username or "", user.full_name, referred_by)

    # Отправляем приветствие с баннером
    await send_menu(
        message,
        get_welcome_text(user.full_name, referral_code),
        reply_markup=main_menu_keyboard()
    )

    # Если пришёл по рефералке, начисляем бонус рефереру
    if referred_by:
        ref = db.get_referral(referred_by, user.id)
        if ref and not ref['is_rewarded']:
            db.add_balance_stars(referred_by, REFERRAL_BONUS_STARS)
            db.mark_referral_rewarded(ref['id'], REFERRAL_BONUS_STARS, 0)
            try:
                bot = Bot.get_current()
                await bot.send_message(
                    referred_by,
                    f"{e('gift_box')} <b>По вашей реферальной ссылке зарегистрировался новый пользователь!</b>\n"
                    f"<blockquote>"
                    f"{e('star')} Вам начислено <b>{REFERRAL_BONUS_STARS} звёзд</b> на баланс!\n"
                    f"{e('rocket')} Приглашайте ещё друзей и получайте бонусы!"
                    f"</blockquote>"
                )
            except Exception:
                pass


@router.callback_query(F.data == "main_menu")
async def main_menu_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user = callback.from_user
    user_data = db.get_user(user.id)
    referral_code = user_data['referral_code'] if user_data else None
    await edit_menu(callback, get_welcome_text(user.full_name, referral_code), main_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "assortment")
async def assortment_callback(callback: CallbackQuery):
    text = (
        f"{e('sparkle')}{e('diamond')} <b>АССОРТИМЕНТ</b> {e('diamond')}{e('sparkle')}\n"
        f"\n"
        f"<blockquote>{e('rocket')} Выберите категорию для просмотра</blockquote>"
    )
    await edit_menu(callback, text, assortment_keyboard())
    await callback.answer()


@router.callback_query(F.data == "assort_stars")
async def assort_stars_callback(callback: CallbackQuery):
    prices_text = ""
    examples = [50, 100, 150, 200, 300, 500, 1000]
    for qty in examples:
        price = qty * STARS_PRICE_PER_ONE
        prices_text += f"{e('star')} <b>{qty}</b> звёзд — <b>{price:.2f} BYN</b>\n"

    text = (
        f"{e('star')}{e('sparkle')} <b>TELEGRAM ЗВЁЗДЫ</b> {e('sparkle')}{e('star')}\n"
        f"\n"
        f"<blockquote>"
        f"{e('fire')} <b>Формула цены:</b> 100 звёзд = 5 BYN\n"
        f"{e('diamond')} <b>Минимальный заказ:</b> {MIN_STARS} звёзд\n"
        f"{e('lightning')} <b>Любое количество</b> от {MIN_STARS}!"
        f"</blockquote>\n"
        f"\n"
        f"{e('money')} <b>Примеры цен:</b>\n"
        f"<blockquote>{prices_text.strip()}</blockquote>\n"
        f"\n"
        f"<blockquote>"
        f"{e('gift')} Можно заказать <b>любое количество</b>!\n"
        f"{e('rocket')} Цена рассчитывается автоматически!"
        f"</blockquote>"
    )
    await edit_menu(callback, text, back_to_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "assort_premium")
async def assort_premium_callback(callback: CallbackQuery):
    text = (
        f"{e('crown')}{e('sparkle')} <b>TELEGRAM ПРЕМИУМ</b> {e('sparkle')}{e('crown')}\n"
        f"\n"
        f"<blockquote>"
        f"{e('fire')} <b>Без захода в аккаунт!</b>\n"
        f"{e('diamond')} Выдаётся <b>подарочная карта</b>"
        f"</blockquote>\n"
        f"\n"
        f"{e('money')} <b>Тарифы:</b>\n"
        f"<blockquote>"
        f"{e('lightning')} <b>1 месяц</b> — <b>{PREMIUM_PRICES[1]:.0f} BYN</b>\n"
        f"{e('fire')} <b>3 месяца</b> — <b>{PREMIUM_PRICES[3]:.0f} BYN</b>\n"
        f"{e('trophy')} <b>6 месяцев</b> — <b>{PREMIUM_PRICES[6]:.0f} BYN</b>\n"
        f"{e('crown')} <b>12 месяцев</b> — <b>{PREMIUM_PRICES[12]:.0f} BYN</b>"
        f"</blockquote>"
    )
    await edit_menu(callback, text, back_to_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "my_orders")
async def my_orders_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    orders = db.get_user_orders(user_id)

    if not orders:
        text = (
            f"{e('cart')} <b>Мои заказы</b>\n\n"
            f"<blockquote>"
            f"{e('cross')} У вас пока нет заказов.\n\n"
            f"{e('gift')} Самое время сделать <b>первую покупку!</b>"
            f"</blockquote>"
        )
    else:
        text = f"{e('cart')} <b>Мои заказы</b> (последние 10):\n\n"
        status_map = {
            'pending': f"{e('lightning')} Ожидает оплаты",
            'paid': f"{e('check')} Оплачен (ожидает подтверждения)",
            'confirmed': f"{e('check')} Подтверждён",
            'in_progress': f"{e('fire')} Выполняется",
            'completed': f"{e('trophy')} Выполнен",
            'rejected': f"{e('cross')} Отклонён"
        }

        for order in orders:
            order_type_text = "Звёзды" if order['order_type'] == 'stars' else "Премиум"
            qty_text = f"{order['quantity']} шт." if order['order_type'] == 'stars' else f"{order['quantity']} мес."
            status_text = status_map.get(order['status'], order['status'])
            target = order['target_username'] or 'Не указан'

            text += (
                f"<blockquote>"
                f"{e('diamond')} <b>Заказ #{order['id']}</b>\n"
                f"Тип: <b>{order_type_text}</b>\n"
                f"Количество: <b>{qty_text}</b>\n"
                f"Кому: @{target}\n"
                f"Цена: <b>{order['price']:.2f} BYN</b>\n"
                f"Статус: {status_text}"
                f"</blockquote>\n"
            )

    await edit_menu(callback, text, back_to_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "support")
async def support_callback(callback: CallbackQuery):
    text = (
        f"{e('medal')} <b>Поддержка</b>\n\n"
        f"<blockquote>"
        f"{e('heart')} Если у вас есть вопросы или проблемы,\n"
        f"напишите администратору.\n\n"
        f"{e('fire')} <b>Мы всегда рады помочь!</b>\n"
        f"{e('sparkle')} Время ответа: <b>до 30 минут</b>"
        f"</blockquote>"
    )
    await edit_menu(callback, text, back_to_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "referral_info")
async def referral_info_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_data = db.get_user(user_id)
    if not user_data:
        await callback.answer("Ошибка!", show_alert=True)
        return

    ref_code = user_data['referral_code']  # теперь без префикса
    balance = db.get_balance_stars(user_id)
    referrals = db.get_referrals_by_referrer(user_id)
    total_referrals = len(referrals)
    rewarded = sum(1 for r in referrals if r['is_rewarded'])

    text = (
        f"{e('gift_box')}{e('sparkle')} <b>Реферальная система</b> {e('sparkle')}{e('gift_box')}\n\n"
        f"<blockquote>"
        f"{e('rocket')} Приглашайте друзей и получайте бонусы!\n\n"
        f"{e('diamond')} Ваш реферальный код:\n"
        f"<code>ref_{ref_code}</code>\n\n"
        f"{e('star')} <b>Ваш баланс звёзд:</b> {balance}\n"
        f"{e('crown')} <b>Приглашено друзей:</b> {total_referrals}\n"
        f"{e('trophy')} <b>Активных (купили):</b> {rewarded}"
        f"</blockquote>\n\n"
        f"<blockquote>"
        f"{e('lightning')} <b>За каждого приглашённого:</b>\n"
        f"{e('gift')} Вы получаете <b>10 звёзд</b>\n"
        f"{e('money')} <b>Дополнительно 5%</b> от суммы его первой покупки"
        f"</blockquote>\n\n"
        f"{e('lightning')} <b>Ваша ссылка:</b>\n"
        f"<code>https://t.me/{BOT_USERNAME}?start=ref_{ref_code}</code>"
    )
    await edit_menu(callback, text, referral_info_keyboard(ref_code))
    await callback.answer()


# Обработчик "скопировать ссылку" (просто показывает ссылку)
@router.callback_query(F.data.startswith("copy_ref_"))
async def copy_ref_callback(callback: CallbackQuery):
    ref_code = callback.data.split("_")[2]
    await callback.answer(
        f"Ваша ссылка: https://t.me/{BOT_USERNAME}?start=ref_{ref_code}",
        show_alert=True
    )