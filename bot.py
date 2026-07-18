
# bot.py

import asyncio
import logging
import sys
import traceback

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.types import ErrorEvent

from config import BOT_TOKEN
from handlers import start, stars, premium, admin

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger(__name__)


async def error_handler(event: ErrorEvent):
    """Ловим все ошибки и выводим подробно"""
    logger.error("═" * 60)
    logger.error(f"❌ ОШИБКА: {event.exception}")
    logger.error("─" * 60)
    logger.error(traceback.format_exc())
    logger.error("═" * 60)


async def main():
    # Для aiogram 3.2.0 используем parse_mode напрямую
    bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)

    dp = Dispatcher()

    dp.errors.register(error_handler)

    dp.include_router(start.router)
    dp.include_router(stars.router)
    dp.include_router(premium.router)
    dp.include_router(admin.router)

    await bot.delete_webhook(drop_pending_updates=True)

    logger.info("🤖 Бот запущен!")
    logger.info("⭐ Магазин TG Звёзд и Премиума готов к работе!")
    logger.info("💡 Используйте /emoji для получения ID премиум-эмодзи")

    await dp.start_polling(bot)


# ---- АВТОПЕРЕЗАПУСК ----
async def run_with_restart():
    while True:
        try:
            await main()
        except Exception as e:
            logger.error(f"⚠️ Бот упал с ошибкой: {e}")
            logger.info("🔄 Перезапуск через 5 секунд...")
            await asyncio.sleep(5)
        else:
            logger.info("🛑 Бот остановлен корректно.")
            break


if __name__ == "__main__":
    asyncio.run(run_with_restart())
