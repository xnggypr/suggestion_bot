from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.utils.exceptions import BotBlocked

from utils.localization import get_text
from utils import db
import keyboards
import asyncio
from datetime import datetime

class SuggestionFSM(StatesGroup):
    waiting_for_text = State()

class ContactAdminFSM(StatesGroup):
    waiting_for_text = State()
    waiting_for_admin = State()

class AdminReplyFSM(StatesGroup):
    waiting_comment = State()

# ---- Helper: Notification Broadcaster ----
async def notify_authors(bot):
    while True:
        for s_id, u_id, status, comment in db.get_unnotified_suggestions():
            user = db.get_user(u_id)
            lang = user[6] if user else 'ru'
            try:
                if status == 'approved':
                    text = get_text('notify_approved', lang, s_id)
                elif status == 'rejected':
                    text = get_text('notify_rejected', lang, s_id, comment or '')
                else:
                    continue
                await bot.send_message(u_id, text)
                db.set_suggestion_notified(s_id)
            except BotBlocked:
                db.set_suggestion_notified(s_id)
            except Exception:
                pass
        await asyncio.sleep(15)

def register(dp: Dispatcher, admin_ids, channel_username):
    bot = dp.bot

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
            await msg.answer(get_text("profile_stats", lang, profile[1], profile[2], profile[3], profile[4], profile[5]), reply_markup=keyboards.main_menu(lang))

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

    # ==== Битва предложек с ограничением по времени ====
    @dp.message_handler(lambda m: get_text("battle", db.get_user(m.from_user.id)[6] if db.get_user(m.from_user.id) else "ru") in m.text)
    async def do_battle(msg: types.Message, state: FSMContext):
        lang = db.get_user(msg.from_user.id)[6] if db.get_user(msg.from_user.id) else "ru"
        last_battle = db.get_last_battle()
        now = datetime.now()
        if last_battle and last_battle[2]:  # ended_at
            ended = datetime.fromisoformat(str(last_battle[2]))
            if ended > now:
                dt_str = ended.strftime('%d.%m %H:%M')
                await msg.answer(get_text("battle_time_info", lang, dt_str))
                sug_ids = [int(x) for x in last_battle[3].split(",")]
                await msg.answer(get_text("battle_start", lang), reply_markup=keyboards.battle_voting(sug_ids, lang))
                return
            else:
                await msg.answer(get_text("battle_ended", lang))
        candidates = db.get_battle_candidates()
        if len(candidates) < 2:
            await msg.answer("Недостаточно идей для битвы." if lang == "ru" else "Not enough ideas for battle.")
            return
        sug_ids = [c[0] for c in candidates]
        db.save_battle(sug_ids, duration_hours=24)
        texts = [f"#{i+1}: {candidates[i][2]}" for i in range(len(candidates))]
        for t in texts:
            await msg.answer(t)
        last_battle = db.get_last_battle()
        ended = datetime.fromisoformat(str(last_battle[2]))
        dt_str = ended.strftime('%d.%m %H:%M')
        await msg.answer(get_text("battle_time_info", lang, dt_str))
        await msg.answer(get_text("battle_start", lang), reply_markup=keyboards.battle_voting(sug_ids, lang))

    # --- Голосование с защитой от повтора и строгим учетом времени битвы ---
    @dp.callback_query_handler(lambda c: c.data.startswith("vote_"))
    async def vote_handler(call: types.CallbackQuery):
        sug_id = int(call.data.replace("vote_", ""))
        last_battle = db.get_last_battle()
        if last_battle is None:
            await call.answer("Нет активной битвы.", show_alert=True)
            return
        ended = datetime.fromisoformat(str(last_battle[2]))
        now = datetime.now()
        if ended < now:
            await call.answer(get_text("battle_ended", db.get_user(call.from_user.id)[6]), show_alert=True)
            return
        # Проверка на повторное голосование
        conn = db.get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM votes WHERE battle_id = ? AND user_id = ?", (last_battle[0], call.from_user.id))
        already = cursor.fetchone()
        if already:
            await call.answer(get_text("already_voted", db.get_user(call.from_user.id)[6]), show_alert=True)
            conn.close()
            return
        # Записать голос
        cursor.execute("INSERT INTO votes (battle_id, user_id, suggestion_id) VALUES (?, ?, ?)", (last_battle[0], call.from_user.id, sug_id))
        conn.commit()
        conn.close()
        
        # Добавить баллы автору идеи
        idea = next((i for i in db.get_approved_suggestions(30) if i[0] == sug_id), None)
        if idea:
            db.add_points(idea[1], 20)
            winner = db.get_user(idea[1])
            lang = winner[6] if winner else "ru"
            await call.message.answer(get_text("winner", lang, winner[1]))
        await call.answer(get_text("vote", db.get_user(call.from_user.id)[6]))

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

    # ---- УСОВЕРШЕНСТВОВАННАЯ АДМИН ПАНЕЛЬ ---- #

    @dp.message_handler(lambda m: m.from_user.id in admin_ids and (get_text("admin_panel", db.get_user(m.from_user.id)[6] if db.get_user(m.from_user.id) else "ru") in m.text or m.text.startswith('/admin')))
    async def admin_panel(msg: types.Message, state: FSMContext):
        lang = db.get_user(msg.from_user.id)[6] if db.get_user(msg.from_user.id) else "ru"
        await msg.answer("Админ-панель.\nВыберите статус для просмотра:\n1. ⏳ На модерации (/pending)\n2. ✅ Одобренные (/approved)\n3. ❌ Отклонённые (/rejected)\n4. 👀 Все идеи (/all)\n\nДля поиска по ID: /ideaID [id]", reply_markup=keyboards.admin_panel(lang))

    @dp.message_handler(commands=['pending', 'approved', 'rejected', 'all'], user_id=lambda uid: uid in admin_ids)
    async def admin_list(msg: types.Message):
        lang = db.get_user(msg.from_user.id)[6] if db.get_user(msg.from_user.id) else "ru"
        status = msg.text[1:]
        if status == 'all':
            suggestions = db.get_pending_suggestions() + db.get_approved_suggestions(50)
            status_name = "Все"
        else:
            if status == 'pending':
                suggestions = db.get_pending_suggestions()
                status_name = "На модерации"
            elif status == 'approved':
                suggestions = db.get_approved_suggestions(50)
                status_name = "Одобренные"
            else:
                # For rejected
                conn = db.get_conn()
                cursor = conn.cursor()
                cursor.execute("SELECT id, user_id, content FROM suggestion WHERE status = 'rejected' ORDER BY created_at DESC LIMIT 50")
                suggestions = cursor.fetchall()
                conn.close()
                status_name = "Отклонённые"
        
        if not suggestions:
            await msg.answer(f"Нет идей ({status_name})")
            return
            
        for sid, uid, content in suggestions[:15]:
            user = db.get_user(uid)
            uname = user[1] if user else uid
            await msg.answer(f"#{sid} от @{uname}\n{content}", reply_markup=keyboards.idea_actions(sid, lang))

    @dp.message_handler(lambda m: m.text and m.text.startswith('/ideaID'), user_id=lambda uid: uid in admin_ids)
    async def idea_by_id(msg: types.Message):
        args = msg.text.split()
        if len(args) < 2 or not args[1].isdigit():
            await msg.answer("Используйте: /ideaID [id]")
            return
        iid = int(args[1])
        conn = db.get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT id, user_id, content, status FROM suggestion WHERE id = ?", (iid,))
        res = cursor.fetchone()
        conn.close()
        if not res:
            await msg.answer("Идея не найдена.")
            return
        sid, uid, content, status = res
        user = db.get_user(uid)
        uname = user[1] if user else uid
        lang = db.get_user(msg.from_user.id)[6] if db.get_user(msg.from_user.id) else "ru"
        await msg.answer(f"#{sid} [{status}] от @{uname}\n{content}", reply_markup=keyboards.idea_actions(sid, lang))

    @dp.callback_query_handler(lambda c: c.data.startswith("approve_") or c.data.startswith("reject_") or c.data.startswith("auto_"))
    async def moderate_idea(call: types.CallbackQuery, state: FSMContext):
        action, sid = call.data.split("_")
        sid = int(sid)
        # Убран фильтр по user_id, теперь админ может модерировать любую идею, включая свою
        lang = db.get_user(call.from_user.id)[6] if db.get_user(call.from_user.id) else "ru"
        
        # Для reject — запрашиваем комментарий
        if action == "reject":
            await state.update_data(suggestion_id=sid)
            await call.message.answer("Напишите причину отклонения / комментарий, или 'нет':")
            await AdminReplyFSM.waiting_comment.set()
            await call.answer()
        else:
            if action == "approve":
                db.approve_suggestion(sid)
                await call.answer("Одобрено.")
            elif action == "auto":
                db.approve_suggestion(sid, admin_comment=get_text("idea_status_approved", lang))
                await call.answer("Спасибо за идею!")
            await call.message.edit_reply_markup(None)

    @dp.message_handler(state=AdminReplyFSM.waiting_comment, user_id=lambda uid: uid in admin_ids)
    async def admin_send_reject_comment(msg: types.Message, state: FSMContext):
        data = await state.get_data()
        suggestion_id = data.get("suggestion_id")
        comment = msg.text
        db.reject_suggestion(suggestion_id, admin_comment=comment if comment.lower() != 'нет' else None)
        await msg.answer("Предложка отклонена.")
        await state.finish()

    # Команда/кнопка топа недели
    @dp.message_handler(commands=["weektop"])
    async def weektop(msg: types.Message):
        lang = db.get_user(msg.from_user.id)[6] if db.get_user(msg.from_user.id) else "ru"
        top = db.get_week_leaderboard(10)
        if not top:
            await msg.answer(get_text("no_week_winners", lang))
            return
        text = get_text("week_leaderboard", lang)
        for idx, (user_id, username, wpoints) in enumerate(top, 1):
            text += f"{idx}. @{username or user_id} — {wpoints} баллов\n"
        await msg.answer(text)
        
    @dp.message_handler(commands=["leaderboard"], user_id=lambda uid: uid in admin_ids)
    async def leaderboard(msg: types.Message):
        top = db.get_leaderboard(10)
        text = "🏆 Топ участников:\n"
        for idx, (user_id, username, points, level) in enumerate(top, 1):
            text += f"{idx}. @{username or user_id} — {points} баллов ({level})\n"
        await msg.answer(text)
        
    # -------- Уведомления авторам статусов идей --------
    dp.loop.create_task(notify_authors(dp.bot)) # автозапуск при старте
