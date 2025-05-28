import sqlite3

def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS prices (duration TEXT PRIMARY KEY, amount INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS gmail_accounts (email TEXT, password TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS pending_users (user_id INTEGER, duration TEXT, proof_file_id TEXT)''')
    conn.commit()
    conn.close()

def set_price(duration, amount):
    with sqlite3.connect("database.db") as conn:
        conn.execute("REPLACE INTO prices (duration, amount) VALUES (?, ?)", (duration, amount))

def get_price(duration):
    with sqlite3.connect("database.db") as conn:
        cur = conn.cursor()
        cur.execute("SELECT amount FROM prices WHERE duration=?", (duration,))
        row = cur.fetchone()
        return row[0] if row else 0

def add_gmail(email, password):
    with sqlite3.connect("database.db") as conn:
        conn.execute("INSERT INTO gmail_accounts (email, password) VALUES (?, ?)", (email, password))

def get_next_gmail():
    with sqlite3.connect("database.db") as conn:
        cur = conn.cursor()
        cur.execute("SELECT rowid, email, password FROM gmail_accounts ORDER BY rowid ASC LIMIT 1")
        row = cur.fetchone()
        if row:
            conn.execute("DELETE FROM gmail_accounts WHERE rowid=?", (row[0],))
            return row[1], row[2]
    return None

def add_pending_user(user_id, duration, file_id):
    with sqlite3.connect("database.db") as conn:
        conn.execute("INSERT INTO pending_users (user_id, duration, proof_file_id) VALUES (?, ?, ?)", (user_id, duration, file_id))

def get_pending_users():
    with sqlite3.connect("database.db") as conn:
        cur = conn.cursor()
        cur.execute("SELECT user_id, duration FROM pending_users")
        return cur.fetchall()

def approve_user(user_id):
    with sqlite3.connect("database.db") as conn:
        conn.execute("DELETE FROM pending_users WHERE user_id=?", (user_id,))

def reject_user(user_id):
    with sqlite3.connect("database.db") as conn:
        conn.execute("DELETE FROM pending_users WHERE user_id=?", (user_id,))