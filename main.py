import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils.executor import start_webhook, start_polling
from dotenv import load_dotenv

from utils.db import setup_db
import handlers
import middlewares
from handlers import notify_authors

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
ADMIN_IDS = [int(i) for i in os.getenv("ADMIN_IDS", "").split(",") if i]

WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEBHOOK_PATH = "/webhook"
WEBAPP_HOST = "0.0.0.0"
WEBAPP_PORT = int(os.environ.get("PORT", 10000))

bot = Bot(token=BOT_TOKEN, parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot, storage=MemoryStorage())

setup_db()
middlewares.setup(dp, CHANNEL_USERNAME)
handlers.register(dp, ADMIN_IDS, CHANNEL_USERNAME)

async def on_startup(dp):
    if WEBHOOK_URL:
        await bot.set_webhook(WEBHOOK_URL + WEBHOOK_PATH)
    asyncio.create_task(notify_authors(bot))

async def on_shutdown(dp):
    if WEBHOOK_URL:
        await bot.delete_webhook()

if WEBHOOK_URL:
    start_webhook(
        dispatcher=dp,
        webhook_path=WEBHOOK_PATH,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        skip_updates=True,
        host=WEBAPP_HOST,
        port=WEBAPP_PORT,
    )
else:
    start_polling(dp, skip_updates=True, on_startup=on_startup, on_shutdown=on_shutdown)
