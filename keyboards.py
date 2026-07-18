# keyboards.py

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import REVIEWS_LINK, PREMIUM_PRICES, STAR_PACKS, STARS_PRICE_PER_ONE


def main_menu_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Купить TG Звёзды", callback_data="buy_stars")],
        [InlineKeyboardButton(text="👑 Купить TG Премиум", callback_data="buy_premium")],
        [
            InlineKeyboardButton(text="🛒 Мои заказы", callback_data="my_orders"),
            InlineKeyboardButton(text="✨ Ассортимент", callback_data="assortment")
        ],
        [
            InlineKeyboardButton(text="💬 Отзывы", url=REVIEWS_LINK),
            InlineKeyboardButton(text="🆘 Поддержка", callback_data="support")
        ],
        [InlineKeyboardButton(text="🎁 Реферальная система", callback_data="referral_info")]
    ])
    return keyboard


def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")]
    ])
    return keyboard


def stars_target_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎁 Себе", callback_data="stars_target_self"),
            InlineKeyboardButton(text="👤 Другому", callback_data="stars_target_other")
        ],
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")]
    ])
    return keyboard


def stars_packs_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с готовыми паками звёзд + кнопка своего количества"""
    buttons = []

    row = []
    for pack in STAR_PACKS:
        price = pack["amount"] * STARS_PRICE_PER_ONE
        row.append(InlineKeyboardButton(
            text=f"{pack['label']} • {price:.1f} BYN",
            callback_data=f"stars_pack_{pack['amount']}"
        ))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton(
        text="✏️ Своё количество",
        callback_data="stars_custom"
    )])

    buttons.append([InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def premium_target_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎁 Себе", callback_data="premium_target_self"),
            InlineKeyboardButton(text="👤 Другому", callback_data="premium_target_other")
        ],
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")]
    ])
    return keyboard


def premium_duration_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"💎 1 месяц • {PREMIUM_PRICES[1]:.0f} BYN",
            callback_data="premium_months_1"
        )],
        [InlineKeyboardButton(
            text=f"🔥 3 месяца • {PREMIUM_PRICES[3]:.0f} BYN",
            callback_data="premium_months_3"
        )],
        [InlineKeyboardButton(
            text=f"🏆 6 месяцев • {PREMIUM_PRICES[6]:.0f} BYN",
            callback_data="premium_months_6"
        )],
        [InlineKeyboardButton(
            text=f"👑 12 месяцев • {PREMIUM_PRICES[12]:.0f} BYN",
            callback_data="premium_months_12"
        )],
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")]
    ])
    return keyboard


def payment_method_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="💳 CryptoBot (USDT/TON/BTC)",
            callback_data="pay_crypto"
        )],
        [InlineKeyboardButton(
            text="🏦 BYN перевод (карта/банк)",
            callback_data="pay_byn"
        )],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_order")],
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")]
    ])
    return keyboard


def payment_link_keyboard(pay_url: str, order_id: int) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить", url=pay_url)],
        [InlineKeyboardButton(
            text="🔄 Проверить оплату",
            callback_data=f"check_payment_{order_id}"
        )],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_order")],
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")]
    ])
    return keyboard


def byn_payment_keyboard(order_id: int) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="✅ Я оплатил",
            callback_data=f"byn_paid_{order_id}"
        )],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_order")],
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")]
    ])
    return keyboard


def after_purchase_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💖 Оставить отзыв", url=REVIEWS_LINK)],
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")]
    ])
    return keyboard


def confirm_order_keyboard(order_type: str) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="✅ Подтвердить заказ",
            callback_data=f"confirm_order_{order_type}"
        )],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_order")],
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")]
    ])
    return keyboard


def admin_order_keyboard(order_id: int) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="✅ Подтвердить",
            callback_data=f"admin_confirm_{order_id}"
        )],
        [InlineKeyboardButton(
            text="⚡ Начать выполнение",
            callback_data=f"admin_progress_{order_id}"
        )],
        [InlineKeyboardButton(
            text="🏆 Выполнено",
            callback_data=f"admin_complete_{order_id}"
        )],
        [InlineKeyboardButton(
            text="❌ Отклонить",
            callback_data=f"admin_reject_{order_id}"
        )]
    ])
    return keyboard


def assortment_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Telegram Звёзды", callback_data="assort_stars")],
        [InlineKeyboardButton(text="👑 Telegram Premium", callback_data="assort_premium")],
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")]
    ])
    return keyboard

# ---------- НОВЫЕ КЛАВИАТУРЫ ----------
def referral_info_keyboard(referral_code: str) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📋 Скопировать ссылку",
            callback_data=f"copy_ref_{referral_code}"
        )],
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")]
    ])
    return keyboard

def promo_skip_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ Пропустить (без промокода)", callback_data="skip_promo")],
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")]
    ])
    return keyboard