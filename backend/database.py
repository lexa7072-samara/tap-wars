import sqlite3
from typing import Dict, List, Optional
from datetime import datetime

class Database:
    def __init__(self, db_path: str = "game.db"):
        self.db_path = db_path
        self.connection = None
        
    async def init(self):
        self.connection = sqlite3.connect(self.db_path)
        cursor = self.connection.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                full_name TEXT,
                balance INTEGER DEFAULT 0,
                total_score INTEGER DEFAULT 0,
                games_played INTEGER DEFAULT 0,
                referred_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_tickets (
                user_id INTEGER,
                game_type TEXT,
                count INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, game_type)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS games (
                game_id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_type TEXT,
                status TEXT,
                max_players INTEGER,
                ticket_price INTEGER,
                prize_pool INTEGER,
                duration INTEGER,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS game_players (
                game_id INTEGER,
                user_id INTEGER,
                taps INTEGER DEFAULT 0,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (game_id) REFERENCES games(game_id),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS winnings (
                win_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                game_id INTEGER,
                amount INTEGER,
                claimed BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (game_id) REFERENCES games(game_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS withdraw_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount INTEGER,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')
        
        self.connection.commit()
        
    async def add_user(self, user_id: int, username: str, first_name: str, referred_by: Optional[int] = None):
        cursor = self.connection.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO users (user_id, username, first_name, referred_by)
            VALUES (?, ?, ?, ?)
        ''', (user_id, username, first_name, referred_by))
        self.connection.commit()
    
    async def update_user_score(self, user_id: int, username: str, full_name: str, score: int):
        cursor = self.connection.cursor()
        cursor.execute('''
            UPDATE users 
            SET username = ?, full_name = ?, total_score = total_score + ?, games_played = games_played + 1
            WHERE user_id = ?
        ''', (username, full_name, score, user_id))
        self.connection.commit()
        
    async def get_user(self, user_id: int) -> Dict:
        cursor = self.connection.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        
        if row:
            return {
                "user_id": row[0],
                "username": row[1],
                "first_name": row[2],
                "full_name": row[3],
                "balance": row[4],
                "total_score": row[5],
                "games_played": row[6]
            }
        return None
    
    async def create_game(self, game_type: str, status: str, max_players: int, ticket_price: int, prize_pool: int, duration: int, start_time, end_time) -> int:
        cursor = self.connection.cursor()
        cursor.execute('''
            INSERT INTO games (game_type, status, max_players, ticket_price, prize_pool, duration, start_time, end_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (game_type, status, max_players, ticket_price, prize_pool, duration, start_time, end_time))
        self.connection.commit()
        return cursor.lastrowid
    
    async def get_active_game(self, game_type: str = None) -> Dict:
        cursor = self.connection.cursor()
        if game_type:
            cursor.execute('SELECT * FROM games WHERE game_type = ? AND (status = "waiting" OR status = "active") LIMIT 1', (game_type,))
        else:
            cursor.execute('SELECT * FROM games WHERE status = "waiting" OR status = "active" LIMIT 1')
        row = cursor.fetchone()
        
        if row:
            return {
                "game_id": row[0],
                "game_type": row[1],
                "status": row[2],
                "max_players": row[3],
                "ticket_price": row[4],
                "prize_pool": row[5],
                "duration": row[6]
            }
        return None
    
    async def add_player_to_game(self, game_id: int, user_id: int):
        cursor = self.connection.cursor()
        cursor.execute('INSERT OR IGNORE INTO game_players (game_id, user_id) VALUES (?, ?)', (game_id, user_id))
        self.connection.commit()
    
    async def get_game_players_count(self, game_id: int) -> int:
        cursor = self.connection.cursor()
        cursor.execute('SELECT COUNT(*) FROM game_players WHERE game_id = ?', (game_id,))
        count = cursor.fetchone()[0]
        return count
    
    async def update_player_taps(self, game_id: int, user_id: int, taps: int):
        cursor = self.connection.cursor()
        cursor.execute('UPDATE game_players SET taps = ? WHERE game_id = ? AND user_id = ?', (taps, game_id, user_id))
        self.connection.commit()
    
    async def update_game_status(self, game_id: int, status: str):
        cursor = self.connection.cursor()
        cursor.execute('UPDATE games SET status = ? WHERE game_id = ?', (status, game_id))
        self.connection.commit()
    
    async def add_winnings(self, user_id: int, amount: int, game_id: int):
        cursor = self.connection.cursor()
        cursor.execute('INSERT INTO winnings (user_id, game_id, amount, claimed) VALUES (?, ?, ?, 0)', (user_id, game_id, amount))
        self.connection.commit()
        await self.update_user_balance(user_id, amount)
    
    async def update_user_balance(self, user_id: int, amount: int):
        cursor = self.connection.cursor()
        cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
        self.connection.commit()
    
    async def get_leaderboard(self, limit: int = 100) -> List[Dict]:
        cursor = self.connection.cursor()
        cursor.execute('''
            SELECT user_id, username, full_name, total_score 
            FROM users 
            ORDER BY total_score DESC 
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        return [{"user_id": r[0], "username": r[1], "full_name": r[2] or r[1], "score": r[3]} for r in rows]
    
    async def check_user_ticket(self, user_id: int, game_type: str) -> bool:
        cursor = self.connection.cursor()
        cursor.execute('''
            SELECT count FROM user_tickets 
            WHERE user_id = ? AND game_type = ? AND count > 0
        ''', (user_id, game_type))
        row = cursor.fetchone()
        return row is not None
    
    async def use_ticket(self, user_id: int, game_type: str):
        cursor = self.connection.cursor()
        cursor.execute('''
            UPDATE user_tickets 
            SET count = count - 1 
            WHERE user_id = ? AND game_type = ? AND count > 0
        ''', (user_id, game_type))
        self.connection.commit()
    
    async def add_ticket(self, user_id: int, game_type: str, count: int = 1):
        cursor = self.connection.cursor()
        cursor.execute('''
            INSERT INTO user_tickets (user_id, game_type, count)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, game_type) 
            DO UPDATE SET count = count + ?
        ''', (user_id, game_type, count, count))
        self.connection.commit()
        print(f"✅ Added {count} {game_type} ticket(s) to user {user_id}")
    
    async def withdraw_stars(self, user_id: int, amount: int) -> bool:
        cursor = self.connection.cursor()
        
        cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        
        if not row or row[0] < amount:
            return False
        
        cursor.execute('UPDATE users SET balance = balance - ? WHERE user_id = ?', (amount, user_id))
        self.connection.commit()
        
        cursor.execute('''
            INSERT INTO withdraw_requests (user_id, amount, status, created_at)
            VALUES (?, ?, 'pending', CURRENT_TIMESTAMP)
        ''', (user_id, amount))
        self.connection.commit()
        
        return True
    
    async def get_withdraw_history(self, user_id: int) -> List[Dict]:
        cursor = self.connection.cursor()
        cursor.execute('''
            SELECT * FROM withdraw_requests 
            WHERE user_id = ? 
            ORDER BY created_at DESC
        ''', (user_id,))
        rows = cursor.fetchall()
        
        return [{
            "id": r[0],
            "amount": r[2],
            "status": r[3],
            "created_at": r[4],
            "completed_at": r[5]
        } for r in rows]
    
    async def get_withdraw_info(self, user_id: int) -> Dict:
        cursor = self.connection.cursor()
        
        cursor.execute('''
            SELECT SUM(amount) FROM withdraw_requests 
            WHERE user_id = ? AND status = 'pending'
        ''', (user_id,))
        pending = cursor.fetchone()[0] or 0
        
        return {
            "min_amount": 100,
            "fee": 0,
            "pending": pending
        }
    
    async def get_withdraw_requests(self, status: str = None) -> List[Dict]:
        cursor = self.connection.cursor()
        if status:
            cursor.execute('SELECT * FROM withdraw_requests WHERE status = ? ORDER BY created_at DESC', (status,))
        else:
            cursor.execute('SELECT * FROM withdraw_requests ORDER BY created_at DESC')
        rows = cursor.fetchall()
        
        return [{
            "id": r[0],
            "user_id": r[1],
            "amount": r[2],
            "status": r[3],
            "created_at": r[4],
            "completed_at": r[5]
        } for r in rows]
