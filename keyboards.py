from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from utils.localization import get_text

def main_menu(lang="ru"):
    return ReplyKeyboardMarkup(resize_keyboard=True).add(
        KeyboardButton(get_text("send_idea", lang)),
        KeyboardButton(get_text("my_profile", lang)),
        KeyboardButton(get_text("history", lang)),
        KeyboardButton(get_text("battle", lang)),
        KeyboardButton(get_text("contact_admin", lang)),
        KeyboardButton(get_text("choose_language", lang)),
    )

def subscribe_check(lang="ru", channel_username="@example_channel"):
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton(get_text("subscribe", lang), url=f"https://t.me/{channel_username.lstrip('@')}"),
        InlineKeyboardButton(get_text("check_sub", lang), callback_data="check_subscription"),
    )
    return kb

def admin_panel(lang="ru"):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton(get_text("admin_panel", lang)))
    return kb

def idea_actions(suggestion_id, lang="ru"):
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton(get_text("approve", lang), callback_data=f"approve_{suggestion_id}"),
        InlineKeyboardButton(get_text("reject", lang), callback_data=f"reject_{suggestion_id}"),
        InlineKeyboardButton(get_text("respond_auto", lang), callback_data=f"auto_{suggestion_id}"),
    )
    return kb

def battle_voting(ids, lang="ru"):
    kb = InlineKeyboardMarkup()
    for i, suggestion_id in enumerate(ids):
        kb.add(InlineKeyboardButton(f"{get_text('vote', lang)} #{i+1}", callback_data=f"vote_{suggestion_id}"))
    return kb

def admin_select(admins, lang="ru"):
    kb = InlineKeyboardMarkup()
    for uid, uname in admins:
        kb.add(InlineKeyboardButton(uname or str(uid), callback_data=f"contact_{uid}"))
    kb.add(InlineKeyboardButton("Все админы", callback_data="contact_all"))
    return kb

def language_menu(current_lang="ru"):
    kb = InlineKeyboardMarkup(row_width=2)
    for code, name in [("ru", "Русский"), ("en", "English")]:
        if code == current_lang:
            txt = f"✅ {name}"
        else:
            txt = name
        kb.add(InlineKeyboardButton(txt, callback_data=f"lang_{code}"))
    return kb