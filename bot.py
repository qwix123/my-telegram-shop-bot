# bot.py

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import ErrorEvent

from config import BOT_TOKEN
from handlers import start, stars, premium, admin

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger(__name__)


async def main():
    # Создаём бота с правильным синтаксисом для aiogram 3.4.1
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    dp = Dispatcher()

    # Подключаем роутеры
    dp.include_router(start.router)
    dp.include_router(stars.router)
    dp.include_router(premium.router)
    dp.include_router(admin.router)

    # Удаляем вебхук и сбрасываем обновления
    await bot.delete_webhook(drop_pending_updates=True)

    logger.info("🤖 Бот запущен!")
    logger.info("⭐ Магазин TG Звёзд и Премиума готов к работе!")
    logger.info("💡 Используйте /emoji для получения ID премиум-эмодзи")

    # Запускаем поллинг
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
