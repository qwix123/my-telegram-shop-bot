# config.py

BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"

# ID админ-группы (куда приходят заказы)
ADMIN_GROUP_ID = -1001234567890  # Замените на свой ID группы

# Ссылка на группу отзывов
REVIEWS_LINK = "https://t.me/+oQMUTrP-StxjNjg6"

# Админы (user_id)
ADMINS = [123456789]  # Замените на свои ID

# Цены звёзд (за 100 звёзд = 5 BYN)
STARS_PRICE_PER_ONE = 0.05  # 5 / 100 = 0.05 BYN за 1 звезду
MIN_STARS = 50

# Цены премиума (BYN)
PREMIUM_PRICES = {
    1: 20.0,
    3: 45.0,
    6: 70.0,
    12: 100.0
}

# Премиум эмодзи ID (используем custom emoji)
# Это ID кастомных премиум-эмодзи из Telegram
EMOJI_STAR = "⭐"
EMOJI_FIRE = "🔥"
EMOJI_CHECK = "✅"
EMOJI_CROSS = "❌"
EMOJI_DIAMOND = "💎"
EMOJI_CROWN = "👑"
EMOJI_ROCKET = "🚀"
EMOJI_GIFT = "🎁"
EMOJI_MONEY = "💰"
EMOJI_CART = "🛒"
EMOJI_SPARKLE = "✨"
EMOJI_HEART = "💖"
EMOJI_MEDAL = "🏅"
EMOJI_TROPHY = "🏆"
EMOJI_LIGHTNING = "⚡"