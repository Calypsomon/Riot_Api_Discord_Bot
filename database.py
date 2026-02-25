import sqlite3

DB_NAME = "users.db"

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            discord_id TEXT PRIMARY KEY,
            puuid TEXT NOT NULL
        )
        """)

def add_user(discord_id, puuid):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO users (discord_id, puuid) VALUES (?, ?)",
            (discord_id, puuid)
        )

def get_puuid(discord_id):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT puuid FROM users WHERE discord_id = ?",
            (discord_id,)
        )
        result = cursor.fetchone()
        return result[0] if result else None