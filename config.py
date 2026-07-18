# config.py

BOT_TOKEN = "8478886630:AAFX2caUcC4jTfONESp_HLb6McNMP_ALkqc"
ADMIN_GROUP_ID = -1003683205881
REVIEWS_LINK = "https://t.me/+oQMUTrP-StxjNjg6"
ADMINS = [6355052629]

# CryptoBot
CRYPTOBOT_TOKEN = "506052:AATVaTsKcRGtDhgWgvOOsHNqeeTiqkDjcDX"
CRYPTOBOT_API_URL = "https://pay.crypt.bot/api"

# Курс BYN к USD (примерный, обновляйте)
BYN_TO_USD = 0.31  # 1 BYN = 0.31 USD

# Реквизиты для приёма BYN-переводов
BANK_CARD_NUMBER = "4255 1901 3563 2373"
BANK_CARD_HOLDER = "Иванов Иван Иванович"
BANK_NAME = "Беларусбанк"

# Цена звёзд: 50 звёзд = 2.6 BYN
STARS_PRICE_PER_ONE = 0.052   # 2.6 / 50
MIN_STARS = 50

PREMIUM_PRICES = {
    1: 12.0,
    3: 45.0,
    6: 55.0,
    12: 100.0
}

# Готовые паки звёзд
STAR_PACKS = [
    {"amount": 50, "label": "50 ⭐"},
    {"amount": 100, "label": "100 ⭐"},
    {"amount": 150, "label": "150 ⭐"},
    {"amount": 250, "label": "250 ⭐"},
    {"amount": 500, "label": "500 ⭐"},
    {"amount": 1000, "label": "1000 ⭐"},
]

# Настройки реферальной системы
REFERRAL_BONUS_STARS = 10
REFERRAL_BONUS_PERCENT = 5
REMINDER_DELAY_SECONDS = 900

# Имя бота (без @)
BOT_USERNAME = "belarus_PRODUCTbot"

DEFAULT_EMOJI = {
    "star": "⭐",
    "fire": "🔥",
    "check": "✅",
    "cross": "❌",
    "diamond": "💎",
    "crown": "👑",
    "rocket": "🚀",
    "gift": "🎁",
    "money": "💰",
    "cart": "🛒",
    "sparkle": "✨",
    "heart": "💖",
    "medal": "🏅",
    "trophy": "🏆",
    "lightning": "⚡",
    "clock": "⏳",
    "gift_box": "🎁",
}

EMOJI_MEANINGS = {
    "star": ["⭐", "🌟", "★", "✨", "💫"],
    "fire": ["🔥", "🌶", "♨"],
    "check": ["✅", "✔", "☑", "🆗"],
    "cross": ["❌", "✖", "🚫", "⛔"],
    "diamond": ["💎", "🔷", "🔹"],
    "crown": ["👑", "🤴", "👸"],
    "rocket": ["🚀", "🛸", "✈"],
    "gift": ["🎁", "🎀", "🎉"],
    "money": ["💰", "💵", "💴", "💶", "💷", "💸", "🤑"],
    "cart": ["🛒", "🛍", "🧺"],
    "sparkle": ["✨", "💫", "🌟", "⭐"],
    "heart": ["💖", "❤", "💕", "💗", "💓", "❣", "💝"],
    "medal": ["🏅", "🎖", "🥇", "🥈", "🥉"],
    "trophy": ["🏆", "🎗", "🥇"],
    "lightning": ["⚡", "🌩", "☇"],
    "clock": ["⏳", "⌛"],
    "gift_box": ["🎁", "🎀", "🎉"],
}