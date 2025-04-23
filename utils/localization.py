LANGUAGES = {
    "ru": {
        "welcome": "👋 Добро пожаловать в Бот Предложек!",
        "check_sub": "Проверить подписку",
        "subscribe": "Подписаться",
        "need_subscription": "Для продолжения подпишитесь на канал:",
        "send_idea": "✉️ Отправить идею",
        "my_profile": "🧑‍💼 Профиль",
        "history": "🗂 Мои идеи",
        "battle": "🔥 Битва предложек",
        "contact_admin": "💬 Связаться с админом",
        "choose_language": "Выберите язык 🔄",
        "idea_sent": "Идея отправлена на модерацию!",
        "idea_status_approved": "✅ Ваша идея одобрена и опубликована!",
        "idea_status_rejected": "❌ Ваша идея отклонена.",
        "idea_status_pending": "⏳ Идея на модерации.",
        "no_ideas": "У вас пока нет идей.",
        "profile_stats": "Предложено: {0}\nОдобрено: {1}\nБаллов: {2}\nУровень: {3}\nБаллов на неделе: {4}",
        "select_admin": "Выберите администратора или отправьте обращение для всех:",
        "send_message_admin": "Отправьте сообщение для админа:",
        "admin_panel": "🛠 Админ-панель",
        "approve": "Одобрить",
        "reject": "Отклонить",
        "respond_auto": "Ответить автосообщением",
        "battle_start": "Начинается Битва Предложек! ⚡️\nГолосуйте за лучшую идею!",
        "vote": "Голосовать",
        "winner": "🏆 Победитель недели: @{0}!",
        "notify_approved": "Ваша идея №{0} одобрена и опубликована!",
        "notify_rejected": "Ваша идея №{0} отклонена. {1}",
        "battle_time_info": "Битва предложек активна до: {0}",
        "battle_ended": "⏳ Время битвы истекло. Голосование закрыто!",
        "already_voted": "Вы уже голосовали в этой битве!",
        "week_leaderboard": "🏅 Топ недели:\n",
        "no_week_winners": "На этой неделе еще нет победителей."
    },
    "en": {
        "welcome": "👋 Welcome to Suggestion Bot!",
        "check_sub": "Check Subscription",
        "subscribe": "Subscribe",
        "need_subscription": "Please subscribe to the channel to continue:",
        "send_idea": "✉️ Submit Idea",
        "my_profile": "🧑‍💼 Profile",
        "history": "🗂 My Ideas",
        "battle": "🔥 Idea Battle",
        "contact_admin": "💬 Contact Admin",
        "choose_language": "Choose language 🔄",
        "idea_sent": "Idea sent for moderation!",
        "idea_status_approved": "✅ Your idea is approved and published!",
        "idea_status_rejected": "❌ Your idea was rejected.",
        "idea_status_pending": "⏳ Idea is pending moderation.",
        "no_ideas": "You have no ideas yet.",
        "profile_stats": "Submitted: {0}\nApproved: {1}\nPoints: {2}\nLevel: {3}\nPoints this week: {4}",
        "select_admin": "Select an admin or send a message to all:",
        "send_message_admin": "Type your message for the admin:",
        "admin_panel": "🛠 Admin Panel",
        "approve": "Approve",
        "reject": "Reject",
        "respond_auto": "Respond with auto-message",
        "battle_start": "Idea Battle starts now! ⚡️\nVote for the best idea!",
        "vote": "Vote",
        "winner": "🏆 Weekly winner: @{0}!",
        "notify_approved": "Your suggestion #{0} has been approved and published!",
        "notify_rejected": "Your suggestion #{0} was rejected. {1}",
        "battle_time_info": "Idea Battle is active until: {0}",
        "battle_ended": "⏳ The battle is over. Voting closed!",
        "already_voted": "You've already voted in this battle!",
        "week_leaderboard": "🏅 Top of the week:\n",
        "no_week_winners": "No winners yet this week."
    }
}

def get_text(key, lang="ru", *args):
    if lang not in LANGUAGES:
        lang = "ru"
    base = LANGUAGES[lang].get(key, "")
    if args:
        base = base.format(*args)
    return base
