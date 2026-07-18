# bot.py

import asyncio
import logging
import sys
import traceback

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


async def error_handler(event: ErrorEvent):
    """Ловим все ошибки и выводим подробно"""
    logger.error("═" * 60)
    logger.error(f"❌ ОШИБКА: {event.exception}")
    logger.error("─" * 60)
    logger.error(traceback.format_exc())
    logger.error("═" * 60)


async def main():
    # Для aiogram 3.4.1 используем DefaultBotProperties
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    dp = Dispatcher()

    dp.errors.register(error_handler)

    dp.include_router(start.router)
    dp.include_router(stars.router)
    dp.include_router(premium.router)
    dp.include_router(admin.router)

    # Удаляем вебхук и сбрасываем ожидающие обновления
    await bot.delete_webhook(drop_pending_updates=True)

    logger.info("🤖 Бот запущен!")
    logger.info("⭐ Магазин TG Звёзд и Премиума готов к работе!")
    logger.info("💡 Используйте /emoji для получения ID премиум-эмодзи")

    # Запускаем поллинг с обработкой конфликтов
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка во время поллинга: {e}")
        raise


# ---- АВТОПЕРЕЗАПУСК С ОБРАБОТКОЙ КОНФЛИКТОВ ----
async def run_with_restart():
    while True:
        try:
            await main()
        except Exception as e:
            # Если конфликт — ждём дольше (30 секунд) и перезапускаем
            if "Conflict" in str(e):
                logger.error("⚠️ Обнаружен конфликт (два бота с одним токеном). Ждём 30 секунд...")
                await asyncio.sleep(30)
            else:
                logger.error(f"⚠️ Бот упал с ошибкой: {e}")
                logger.info("🔄 Перезапуск через 5 секунд...")
                await asyncio.sleep(5)
        else:
            logger.info("🛑 Бот остановлен корректно.")
            break


if __name__ == "__main__":
    asyncio.run(run_with_restart())
