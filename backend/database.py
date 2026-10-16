import sqlite3
import json
import os

DB_FILE = os.getenv("DB_PATH", "users.db")

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS profiles (
            user_id TEXT PRIMARY KEY,
            profile_data TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            full_name TEXT,
            password TEXT
        )
    ''')
    conn.commit()
    conn.close()

def create_user(email: str, full_name: str, password_hash: str):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO users (email, full_name, password) VALUES (?, ?, ?)',
                       (email, full_name, password_hash))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_user(email: str):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT email, full_name, password FROM users WHERE email = ?', (email,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"email": row[0], "full_name": row[1], "password": row[2]}
    return None

def get_profile(user_id: str):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT profile_data FROM profiles WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return json.loads(row[0])
    return None

def save_profile(user_id: str, profile_data: dict):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('SELECT user_id FROM profiles WHERE user_id = ?', (user_id,))
    if cursor.fetchone():
        cursor.execute('UPDATE profiles SET profile_data = ? WHERE user_id = ?', 
                       (json.dumps(profile_data), user_id))
    else:
        cursor.execute('INSERT INTO profiles (user_id, profile_data) VALUES (?, ?)', 
                       (user_id, json.dumps(profile_data)))
    
    conn.commit()
    conn.close()
