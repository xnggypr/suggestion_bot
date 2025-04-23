from aiogram import types
from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.dispatcher.handler import CancelHandler
from aiogram.utils.exceptions import ChatNotFound

from utils.db import get_user, add_user
from utils.localization import get_text

class SubscriptionMiddleware(BaseMiddleware):
    def __init__(self, channel_username):
        super().__init__()
        self.channel_username = channel_username

    async def on_pre_process_update(self, update: types.Update, data: dict):
        user = None
        tg_user = None
        if update.message:
            tg_user = update.message.from_user
        elif update.callback_query:
            tg_user = update.callback_query.from_user
        if tg_user:
            add_user(tg_user.id, tg_user.username or "", language='ru')
        user = get_user(tg_user.id) if tg_user else None
        if tg_user and not await check_subscription(tg_user.id, self.channel_username):
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(get_text("subscribe", user[6] if user else "ru"), url=f"https://t.me/{self.channel_username.lstrip('@')}"))
            markup.add(types.InlineKeyboardButton(get_text("check_sub", user[6] if user else "ru"), callback_data="check_subscription"))
            if update.message:
                await update.message.answer(get_text("need_subscription", user[6] if user else "ru") + f" @{self.channel_username}", reply_markup=markup)
            elif update.callback_query:
                await update.callback_query.message.edit_text(get_text("need_subscription", user[6] if user else "ru") + f" @{self.channel_username}", reply_markup=markup)
            raise CancelHandler()

async def check_subscription(user_id, channel_username):
    from aiogram import Bot
    bot = Bot.get_current()
    try:
        member = await bot.get_chat_member(channel_username, user_id)
        return member.status in ('member', 'administrator', 'creator')
    except ChatNotFound:
        return False

def setup(dp, channel_username):
    dp.middleware.setup(SubscriptionMiddleware(channel_username))