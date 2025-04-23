import sqlite3
from datetime import datetime, timedelta
import random

DB_PATH = "data.db"

def get_conn():
    return sqlite3.connect(DB_PATH)

def setup_db():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        ideas_submitted INTEGER DEFAULT 0,
        ideas_approved INTEGER DEFAULT 0,
        points INTEGER DEFAULT 0,
        level TEXT DEFAULT 'Новичок',
        language TEXT DEFAULT 'ru',
        week_points INTEGER DEFAULT 0,
        last_win_week INTEGER DEFAULT 0
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS suggestion (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        content TEXT,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        published_message_id INTEGER,
        admin_comment TEXT,
        notified INTEGER DEFAULT 0,
        FOREIGN KEY(user_id) REFERENCES user(user_id)
    )""")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS battle (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        started_at TIMESTAMP,
        ended_at TIMESTAMP,
        suggestions TEXT,
        winner_suggestion_id INTEGER DEFAULT NULL
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS votes (
        battle_id INTEGER,
        user_id INTEGER,
        suggestion_id INTEGER,
        voted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    conn.close()

def add_user(user_id, username, language='ru'):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO user (user_id, username, language) VALUES (?, ?, ?)", (user_id, username, language))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def update_language(user_id, lang):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("UPDATE user SET language = ? WHERE user_id = ?", (lang, user_id))
    conn.commit()
    conn.close()

def add_suggestion(user_id, content):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO suggestion (user_id, content) VALUES (?, ?)", (user_id, content))
    cursor.execute("UPDATE user SET ideas_submitted = ideas_submitted + 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def get_user_suggestions(user_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id, content, status FROM suggestion WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
    suggestions = cursor.fetchall()
    conn.close()
    return suggestions

# WEEK helpers
def get_current_week():
    return datetime.now().isocalendar()[1]

def reset_week():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("UPDATE user SET week_points = 0")
    conn.commit()
    conn.close()

def approve_suggestion(suggestion_id, admin_comment=None, published_message_id=None):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("UPDATE suggestion SET status = 'approved', admin_comment = ?, published_message_id = ?, notified = 0 WHERE id = ?", (admin_comment, published_message_id, suggestion_id))
    cursor.execute("""UPDATE user SET ideas_approved = ideas_approved + 1, points = points + 5, week_points = week_points + 5 WHERE user_id = (SELECT user_id FROM suggestion WHERE id = ?)""", (suggestion_id,))
    update_user_level_sql = """
        UPDATE user SET level = 
            CASE
                WHEN points >= 100 THEN 'Гений Идей'
                WHEN points >= 50 THEN 'Продвинутый'
                ELSE 'Новичок'
            END
        WHERE user_id = (SELECT user_id FROM suggestion WHERE id = ?)
    """
    cursor.execute(update_user_level_sql, (suggestion_id,))
    conn.commit()
    conn.close()

def reject_suggestion(suggestion_id, admin_comment=None):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("UPDATE suggestion SET status = 'rejected', admin_comment = ?, notified = 0 WHERE id = ?", (admin_comment, suggestion_id))
    conn.commit()
    conn.close()

def get_pending_suggestions():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id, user_id, content FROM suggestion WHERE status = 'pending' ORDER BY created_at ASC")
    items = cursor.fetchall()
    conn.close()
    return items

def get_approved_suggestions(limit=10):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id, user_id, content FROM suggestion WHERE status = 'approved' ORDER BY RANDOM() LIMIT ?", (limit,))
    suggestions = cursor.fetchall()
    conn.close()
    return suggestions

def save_battle(suggestions_ids, duration_hours=24):
    conn = get_conn()
    cursor = conn.cursor()
    started = datetime.now()
    ended = started + timedelta(hours=duration_hours)
    cursor.execute("INSERT INTO battle (started_at, ended_at, suggestions) VALUES (?, ?, ?)", (started, ended, ",".join(map(str, suggestions_ids))))
    conn.commit()
    conn.close()

def get_last_battle():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id, started_at, ended_at, suggestions, winner_suggestion_id FROM battle ORDER BY started_at DESC LIMIT 1")
    battle = cursor.fetchone()
    conn.close()
    return battle

def set_battle_winner(battle_id, suggestion_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("UPDATE battle SET winner_suggestion_id = ? WHERE id = ?", (suggestion_id, battle_id))
    # победителю начисляются недельные баллы
    cursor.execute("SELECT user_id FROM suggestion WHERE id=?", (suggestion_id,))
    row = cursor.fetchone()
    if row:
        winner_uid = row[0]
        cursor.execute("UPDATE user SET week_points = week_points + 25, last_win_week = ? WHERE user_id = ?", (get_current_week(), winner_uid))
    conn.commit()
    conn.close()

def get_battle_candidates():
    approved = get_approved_suggestions(12)
    return random.sample(approved, min(len(approved), 3))

def add_points(user_id, amount, weekly=True):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("UPDATE user SET points = points + ? WHERE user_id = ?", (amount, user_id))
    if weekly:
        cursor.execute("UPDATE user SET week_points = week_points + ? WHERE user_id = ?", (amount, user_id))
    cursor.execute("""
        UPDATE user SET level = 
            CASE
                WHEN points >= 100 THEN 'Гений Идей'
                WHEN points >= 50 THEN 'Продвинутый'
                ELSE 'Новичок'
            END
        WHERE user_id = ?
    """, (user_id,))
    conn.commit()
    conn.close()

def get_leaderboard(top=10):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username, points, level FROM user ORDER BY points DESC LIMIT ?", (top,))
    top_users = cursor.fetchall()
    conn.close()
    return top_users

def get_week_leaderboard(top=10):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username, week_points FROM user ORDER BY week_points DESC LIMIT ?", (top,))
    data = cursor.fetchall()
    conn.close()
    return data

def get_profile(user_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT username, ideas_submitted, ideas_approved, points, level, week_points FROM user WHERE user_id = ?", (user_id,))
    profile = cursor.fetchone()
    conn.close()
    return profile

# Notified suggestion status
def get_unnotified_suggestions():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id, user_id, status, admin_comment FROM suggestion WHERE notified = 0 AND status IN ('approved','rejected')")
    suggs = cursor.fetchall()
    conn.close()
    return suggs

def set_suggestion_notified(suggestion_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("UPDATE suggestion SET notified = 1 WHERE id = ?", (suggestion_id,))
    conn.commit()
    conn.close()

def delete_db():
    import os
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
