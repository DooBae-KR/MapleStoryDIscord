import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'users.db')

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS favorites 
                 (user_id TEXT, ticker TEXT, name TEXT, PRIMARY KEY(user_id, ticker))''')
    conn.commit()
    conn.close()

def toggle_favorite(user_id: str, ticker: str, name: str) -> bool:
    """
    즐겨찾기에 있으면 삭제하고 False 반환, 없으면 추가하고 True 반환
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("SELECT 1 FROM favorites WHERE user_id=? AND ticker=?", (user_id, ticker))
    exists = c.fetchone()
    
    if exists:
        c.execute("DELETE FROM favorites WHERE user_id=? AND ticker=?", (user_id, ticker))
        added = False
    else:
        c.execute("INSERT INTO favorites (user_id, ticker, name) VALUES (?, ?, ?)", (user_id, ticker, name))
        added = True
        
    conn.commit()
    conn.close()
    return added

def get_favorites(user_id: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT ticker, name FROM favorites WHERE user_id=?", (user_id,))
    rows = c.fetchall()
    conn.close()
    return [{"ticker": r[0], "name": r[1]} for r in rows]
