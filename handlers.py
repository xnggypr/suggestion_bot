from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import StatesGroup, State

from utils.localization import get_text
from utils import db
import keyboards

class SuggestionFSM(StatesGroup):
    waiting_for_text = State()

class ContactAdminFSM(StatesGroup):
    waiting_for_text = State()
    waiting_for_admin = State()

def register(dp: Dispatcher, admin_ids, channel_username):

    @dp.message_handler(commands=["start"])
    async def start(msg: types.Message, state: FSMContext):
        user = db.get_user(msg.from_user.id)
        lang = user[6] if user else "ru"
        await msg.answer(get_text("welcome", lang), reply_markup=keyboards.main_menu(lang))

    @dp.message_handler(lambda m: get_text("send_idea", db.get_user(m.from_user.id)[6] if db.get_user(m.from_user.id) else "ru") in m.text)
    async def new_idea(msg: types.Message, state: FSMContext):
        lang = db.get_user(msg.from_user.id)[6] if db.get_user(msg.from_user.id) else "ru"
        await msg.answer(get_text("send_idea", lang))
        await SuggestionFSM.waiting_for_text.set()

    @dp.message_handler(state=SuggestionFSM.waiting_for_text)
    async def submit_idea(msg: types.Message, state: FSMContext):
        db.add_suggestion(msg.from_user.id, msg.text)
        lang = db.get_user(msg.from_user.id)[6] if db.get_user(msg.from_user.id) else "ru"
        await msg.answer(get_text("idea_sent", lang), reply_markup=keyboards.main_menu(lang))
        await state.finish()

    @dp.message_handler(lambda m: get_text("my_profile", db.get_user(m.from_user.id)[6] if db.get_user(m.from_user.id) else "ru") in m.text)
    async def profile(msg: types.Message, state: FSMContext):
        profile = db.get_profile(msg.from_user.id)
        lang = db.get_user(msg.from_user.id)[6] if db.get_user(msg.from_user.id) else "ru"
        if profile:
            await msg.answer(get_text("profile_stats", lang, profile[1], profile[2], profile[3], profile[4]), reply_markup=keyboards.main_menu(lang))

    @dp.message_handler(lambda m: get_text("history", db.get_user(m.from_user.id)[6] if db.get_user(m.from_user.id) else "ru") in m.text)
    async def my_ideas(msg: types.Message, state: FSMContext):
        lang = db.get_user(msg.from_user.id)[6] if db.get_user(msg.from_user.id) else "ru"
        ideas = db.get_user_suggestions(msg.from_user.id)
        if not ideas:
            await msg.answer(get_text("no_ideas", lang))
            return
        for iid, content, status in ideas[:15]:
            txt = f"#{iid}\n{content}\n"
            if status == "approved":
                txt += get_text("idea_status_approved", lang)
            elif status == "rejected":
                txt += get_text("idea_status_rejected", lang)
            else:
                txt += get_text("idea_status_pending", lang)
            await msg.answer(txt)

    @dp.message_handler(lambda m: get_text("battle", db.get_user(m.from_user.id)[6] if db.get_user(m.from_user.id) else "ru") in m.text)
    async def do_battle(msg: types.Message, state: FSMContext):
        lang = db.get_user(msg.from_user.id)[6] if db.get_user(msg.from_user.id) else "ru"
        candidates = db.get_battle_candidates()
        if len(candidates) < 2:
            await msg.answer("Недостаточно идей для битвы." if lang == "ru" else "Not enough ideas for battle.")
            return
        sug_ids = [c[0] for c in candidates]
        db.save_battle(sug_ids)
        texts = [f"#{i+1}: {candidates[i][2]}" for i in range(len(candidates))]
        for t in texts:
            await msg.answer(t)
        await msg.answer(get_text("battle_start", lang), reply_markup=keyboards.battle_voting(sug_ids, lang))

    @dp.callback_query_handler(lambda c: c.data.startswith("vote_"))
    async def vote_handler(call: types.CallbackQuery):
        sug_id = int(call.data.replace("vote_", ""))
        idea = next((i for i in db.get_approved_suggestions(30) if i[0] == sug_id), None)
        if idea:
            db.add_points(idea[1], 20)
            winner = db.get_user(idea[1])
            lang = winner[6] if winner else "ru"
            await call.message.answer(get_text("winner", lang, winner[1]))
        await call.answer("Голос засчитан!" if call.from_user.language_code == "ru" else "Vote counted!")

    @dp.message_handler(lambda m: get_text("contact_admin", db.get_user(m.from_user.id)[6] if db.get_user(m.from_user.id) else "ru") in m.text)
    async def contact_admin(msg: types.Message, state: FSMContext):
        admins = [(aid, None) for aid in admin_ids]
        lang = db.get_user(msg.from_user.id)[6] if db.get_user(msg.from_user.id) else "ru"
        await msg.answer(get_text("select_admin", lang), reply_markup=keyboards.admin_select(admins, lang))
        await ContactAdminFSM.waiting_for_admin.set()

    @dp.callback_query_handler(lambda c: c.data.startswith("contact_"), state=ContactAdminFSM.waiting_for_admin)
    async def admin_chosen(call: types.CallbackQuery, state: FSMContext):
        admin_id = call.data.replace("contact_", "")
        await state.update_data(selected_admin=admin_id)
        lang = db.get_user(call.from_user.id)[6] if db.get_user(call.from_user.id) else "ru"
        await call.message.answer(get_text("send_message_admin", lang))
        await ContactAdminFSM.waiting_for_text.set()
        await call.answer()

    @dp.message_handler(state=ContactAdminFSM.waiting_for_text)
    async def send_admin_msg(msg: types.Message, state: FSMContext):
        data = await state.get_data()
        admin_id = data.get("selected_admin")
        forward_ids = [a for a in admin_ids] if admin_id == "all" else [int(admin_id)]
        for aid in forward_ids:
            try:
                await msg.bot.send_message(aid, f"Вопрос от @{msg.from_user.username or msg.from_user.id}:\n{msg.text}")
            except:
                pass
        await msg.answer("Сообщение отправлено администратору.")
        await state.finish()

    @dp.message_handler(commands=["language"])
    @dp.message_handler(lambda m: get_text("choose_language", db.get_user(m.from_user.id)[6] if db.get_user(m.from_user.id) else "ru") in m.text)
    async def choose_language(msg: types.Message, state: FSMContext):
        user = db.get_user(msg.from_user.id)
        lang = user[6] if user else "ru"
        await msg.answer(get_text("choose_language", lang), reply_markup=keyboards.language_menu(lang))

    @dp.callback_query_handler(lambda c: c.data.startswith("lang_"))
    async def switch_language(call: types.CallbackQuery):
        lang_code = call.data.replace("lang_", "")
        db.update_language(call.from_user.id, lang_code)
        await call.answer("Язык изменён.", show_alert=False)
        user = db.get_user(call.from_user.id)
        lang = user[6] if user else "ru"
        await call.message.answer(get_text("welcome", lang), reply_markup=keyboards.main_menu(lang))

    @dp.message_handler(lambda m: m.from_user.id in admin_ids and get_text("admin_panel", db.get_user(m.from_user.id)[6] if db.get_user(m.from_user.id) else "ru") in m.text)
    @dp.message_handler(commands=["admin"], user_id=lambda uid: uid in admin_ids)
    async def admin_panel(msg: types.Message, state: FSMContext):
        suggestions = db.get_pending_suggestions()
        lang = db.get_user(msg.from_user.id)[6] if db.get_user(msg.from_user.id) else "ru"
        for sid, uid, content in suggestions[:10]:
            user = db.get_user(uid)
            uname = user[1] if user else uid
            await msg.answer(f"#{sid} от @{uname}\n{content}", reply_markup=keyboards.idea_actions(sid, lang))

    @dp.callback_query_handler(lambda c: c.data.startswith("approve_") or c.data.startswith("reject_") or c.data.startswith("auto_"))
    async def moderate_idea(call: types.CallbackQuery):
        action, sid = call.data.split("_")
        sid = int(sid)
        sugg = db.get_user_suggestions(db.get_user(call.from_user.id)[0])
        lang = db.get_user(call.from_user.id)[6] if db.get_user(call.from_user.id) else "ru"
        if action == "approve":
            db.approve_suggestion(sid)
            await call.answer("Одобрено.")
        elif action == "reject":
            db.reject_suggestion(sid)
            await call.answer("Отклонено.")
        elif action == "auto":
            db.approve_suggestion(sid, admin_comment=get_text("idea_status_approved", lang))
            await call.answer("Спасибо за идею!")
        await call.message.edit_reply_markup(None)