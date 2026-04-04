import sqlite3
from typing import Dict, List, Optional
from datetime import datetime

class Database:
    def __init__(self, db_path: str = "game.db"):
        self.db_path = db_path
        self.connection = None
        
    async def init(self):
        """Инициализация базы данных"""
        self.connection = sqlite3.connect(self.db_path)
        cursor = self.connection.cursor()
        
        # Таблица пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                balance INTEGER DEFAULT 0,
                total_taps INTEGER DEFAULT 0,
                games_played INTEGER DEFAULT 0,
                referred_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица игр
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS games (
                game_id INTEGER PRIMARY KEY AUTOINCREMENT,
                status TEXT,
                max_players INTEGER,
                ticket_price INTEGER,
                prize_pool INTEGER,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица участников игр
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
        
        # Таблица выигрышей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS winnings (
                win_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                game_id INTEGER,
                amount INTEGER,
                claimed BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.connection.commit()
        
    async def add_user(self, user_id: int, username: str, first_name: str, referred_by: Optional[int] = None):
        """Добавить нового пользователя"""
        cursor = self.connection.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO users (user_id, username, first_name, referred_by)
            VALUES (?, ?, ?, ?)
        ''', (user_id, username, first_name, referred_by))
        self.connection.commit()
        
    async def get_user(self, user_id: int) -> Dict:
        """Получить данные пользователя"""
        cursor = self.connection.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        
        if row:
            return {
                "user_id": row[0],
                "username": row[1],
                "first_name": row[2],
                "balance": row[3],
                "total_taps": row[4],
                "games_played": row[5]
            }
        return None
    
    async def create_game(self, status: str, max_players: int, ticket_price: int, prize_pool: int, start_time, end_time) -> int:
        """Создать новую игру"""
        cursor = self.connection.cursor()
        cursor.execute('''
            INSERT INTO games (status, max_players, ticket_price, prize_pool, start_time, end_time)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (status, max_players, ticket_price, prize_pool, start_time, end_time))
        self.connection.commit()
        return cursor.lastrowid
    
    async def get_active_game(self) -> Dict:
        """Получить активную игру"""
        cursor = self.connection.cursor()
        cursor.execute('SELECT * FROM games WHERE status = "waiting" OR status = "active" LIMIT 1')
        row = cursor.fetchone()
        
        if row:
            return {
                "game_id": row[0],
                "status": row[1],
                "max_players": row[2],
                "ticket_price": row[3],
                "prize_pool": row[4]
            }
        return None
    
    async def add_player_to_game(self, game_id: int, user_id: int):
        """Добавить игрока в игру"""
        cursor = self.connection.cursor()
        cursor.execute('INSERT OR IGNORE INTO game_players (game_id, user_id) VALUES (?, ?)', (game_id, user_id))
        self.connection.commit()
    
    async def get_game_players_count(self, game_id: int) -> int:
        """Получить количество игроков в игре"""
        cursor = self.connection.cursor()
        cursor.execute('SELECT COUNT(*) FROM game_players WHERE game_id = ?', (game_id,))
        count = cursor.fetchone()[0]
        return count
    
    async def update_player_taps(self, game_id: int, user_id: int, taps: int):
        """Обновить количество тапов игрока"""
        cursor = self.connection.cursor()
        cursor.execute('UPDATE game_players SET taps = ? WHERE game_id = ? AND user_id = ?', (taps, game_id, user_id))
        self.connection.commit()
    
    async def update_game_status(self, game_id: int, status: str):
        """Обновить статус игры"""
        cursor = self.connection.cursor()
        cursor.execute('UPDATE games SET status = ? WHERE game_id = ?', (status, game_id))
        self.connection.commit()
    
    async def add_winnings(self, user_id: int, amount: int, game_id: int):
        """Добавить выигрыш"""
        cursor = self.connection.cursor()
        cursor.execute('INSERT INTO winnings (user_id, game_id, amount) VALUES (?, ?, ?)', (user_id, game_id, amount))
        self.connection.commit()
    
    async def update_user_balance(self, user_id: int, amount: int):
        """Обновить баланс пользователя"""
        cursor = self.connection.cursor()
        cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
        self.connection.commit()
    
    async def get_leaderboard(self, limit: int = 100) -> List[Dict]:
        """Получить таблицу лидеров"""
        cursor = self.connection.cursor()
        cursor.execute('''
            SELECT user_id, username, total_taps, games_played, balance 
            FROM users 
            ORDER BY total_taps DESC 
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        return [{"user_id": r[0], "username": r[1], "total_taps": r[2], "games_played": r[3], "balance": r[4]} for r in rows]
    
    async def check_user_boost(self, user_id: int, boost_type: str) -> bool:
        """Проверить наличие буста у пользователя"""
        # Временная заглушка - всегда возвращает True
        return True
    
    async def use_boost(self, user_id: int, boost_type: str):
        """Использовать буст"""
        # Временная заглушка
        pass