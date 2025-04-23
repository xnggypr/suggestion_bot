import sqlite3
from datetime import datetime
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
        language TEXT DEFAULT 'ru'
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
        FOREIGN KEY(user_id) REFERENCES user(user_id)
    )""")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS battle (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        started_at TIMESTAMP,
        suggestions TEXT
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

def approve_suggestion(suggestion_id, admin_comment=None, published_message_id=None):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("UPDATE suggestion SET status = 'approved', admin_comment = ?, published_message_id = ? WHERE id = ?", (admin_comment, published_message_id, suggestion_id))
    cursor.execute("""UPDATE user SET ideas_approved = ideas_approved + 1, points = points + 5 WHERE user_id = (SELECT user_id FROM suggestion WHERE id = ?)""", (suggestion_id,))
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
    cursor.execute("UPDATE suggestion SET status = 'rejected', admin_comment = ? WHERE id = ?", (admin_comment, suggestion_id))
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

def save_battle(suggestions_ids):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO battle (started_at, suggestions) VALUES (?, ?)", (datetime.now(), ",".join(map(str, suggestions_ids))))
    conn.commit()
    conn.close()

def get_last_battle():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id, started_at, suggestions FROM battle ORDER BY started_at DESC LIMIT 1")
    battle = cursor.fetchone()
    conn.close()
    return battle

def get_battle_candidates():
    approved = get_approved_suggestions(12)
    return random.sample(approved, min(len(approved), 3))

def add_points(user_id, amount):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("UPDATE user SET points = points + ? WHERE user_id = ?", (amount, user_id))
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

def get_profile(user_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT username, ideas_submitted, ideas_approved, points, level FROM user WHERE user_id = ?", (user_id,))
    profile = cursor.fetchone()
    conn.close()
    return profile

def delete_db():
    import os
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
