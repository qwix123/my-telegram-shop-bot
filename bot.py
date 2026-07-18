import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import BOT_TOKEN
from handlers import start, stars, premium, admin

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)


async def main():
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    dp.include_router(start.router)
    dp.include_router(stars.router)
    dp.include_router(premium.router)
    dp.include_router(admin.router)

    # Жёсткий сброс вебхука и ожидание
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Webhook сброшен, ожидаем 5 секунд...")
    await asyncio.sleep(5)

    logger.info("🤖 Бот запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    while True:
        try:
            asyncio.run(main())
        except Exception as e:
            if "Conflict" in str(e):
                logger.error("⚠️ Конфликт! Ждём 30 секунд и перезапускаем...")
                asyncio.run(asyncio.sleep(30))
            else:
                logger.error(f"⚠️ Ошибка: {e}. Перезапуск через 5 секунд...")
                asyncio.run(asyncio.sleep(5))
