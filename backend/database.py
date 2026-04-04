import aiosqlite
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import json

class Database:
    def __init__(self, db_path: str = "battle_royale.db"):
        self.db_path = db_path
    
    async def init(self):
        async with aiosqlite.connect(self.db_path) as db:
            # Пользователи
            await db.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    balance INTEGER DEFAULT 0,
                    total_games INTEGER DEFAULT 0,
                    total_wins INTEGER DEFAULT 0,
                    total_earned INTEGER DEFAULT 0,
                    referrals INTEGER DEFAULT 0,
                    referred_by INTEGER,
                    free_tickets INTEGER DEFAULT 1,
                    premium_until TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Игры
            await db.execute('''
                CREATE TABLE IF NOT EXISTS games (
                    game_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    status TEXT DEFAULT 'waiting',
                    ticket_price INTEGER,
                    prize_pool INTEGER,
                    players_needed INTEGER,
                    started_at TIMESTAMP,
                    finished_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Участники игр
            await db.execute('''
                CREATE TABLE IF NOT EXISTS game_players (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_id INTEGER,
                    user_id INTEGER,
                    taps INTEGER DEFAULT 0,
                    boosts_used TEXT DEFAULT '[]',
                    position INTEGER,
                    prize INTEGER DEFAULT 0,
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (game_id) REFERENCES games(game_id),
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')
            
            # Бусты
            await db.execute('''
                CREATE TABLE IF NOT EXISTS user_boosts (
                    user_id INTEGER,
                    boost_type TEXT,
                    quantity INTEGER DEFAULT 0,
                    PRIMARY KEY (user_id, boost_type),
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')
            
            # Транзакции
            await db.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    type TEXT,
                    amount INTEGER,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')
            
            # Статистика
            await db.execute('''
                CREATE TABLE IF NOT EXISTS daily_stats (
                    date DATE PRIMARY KEY,
                    total_users INTEGER DEFAULT 0,
                    new_users INTEGER DEFAULT 0,
                    total_games INTEGER DEFAULT 0,
                    total_revenue INTEGER DEFAULT 0
                )
            ''')
            
            await db.commit()
    
    # ========== ПОЛЬЗОВАТЕЛИ ==========
    
    async def add_user(self, user_id: int, username: str, first_name: str, referred_by: int = None):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT OR IGNORE INTO users (user_id, username, first_name, referred_by)
                VALUES (?, ?, ?, ?)
            ''', (user_id, username, first_name, referred_by))
            
            if referred_by:
                await db.execute('''
                    UPDATE users SET referrals = referrals + 1 WHERE user_id = ?
                ''', (referred_by,))
                
                await self.add_transaction(referred_by, "referral", 25, f"Реферал: {username}")
            
            await db.commit()
    
    async def get_user(self, user_id: int) -> Optional[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None
    
    async def update_user_activity(self, user_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE user_id = ?
            ''', (user_id,))
            await db.commit()
    
    async def add_free_ticket(self, user_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                UPDATE users SET free_tickets = free_tickets + 1 WHERE user_id = ?
            ''', (user_id,))
            await db.commit()
    
    async def use_free_ticket(self, user_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT free_tickets FROM users WHERE user_id = ?', (user_id,)) as cursor:
                row = await cursor.fetchone()
                if row and row[0] > 0:
                    await db.execute('''
                        UPDATE users SET free_tickets = free_tickets - 1 WHERE user_id = ?
                    ''', (user_id,))
                    await db.commit()
                    return True
        return False
    
    # ========== ИГРЫ ==========
    
    async def create_game(self, ticket_price: int, players_needed: int) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                INSERT INTO games (ticket_price, prize_pool, players_needed, status)
                VALUES (?, 0, ?, 'waiting')
            ''', (ticket_price, players_needed))
            await db.commit()
            return cursor.lastrowid
    
    async def get_active_game(self) -> Optional[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute('''
                SELECT * FROM games WHERE status = 'waiting' ORDER BY game_id DESC LIMIT 1
            ''') as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None
    
    async def join_game(self, game_id: int, user_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            # Проверка что не участвует уже
            async with db.execute('''
                SELECT id FROM game_players WHERE game_id = ? AND user_id = ?
            ''', (game_id, user_id)) as cursor:
                if await cursor.fetchone():
                    return False
            
            await db.execute('''
                INSERT INTO game_players (game_id, user_id) VALUES (?, ?)
            ''', (game_id, user_id))
            await db.commit()
            return True
    
    async def get_game_players_count(self, game_id: int) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('''
                SELECT COUNT(*) FROM game_players WHERE game_id = ?
            ''', (game_id,)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0
    
    async def get_game_players(self, game_id: int) -> List[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute('''
                SELECT gp.*, u.username, u.first_name 
                FROM game_players gp
                JOIN users u ON gp.user_id = u.user_id
                WHERE gp.game_id = ?
                ORDER BY gp.taps DESC
            ''', (game_id,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    async def start_game(self, game_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                UPDATE games SET status = 'playing', started_at = CURRENT_TIMESTAMP
                WHERE game_id = ?
            ''', (game_id,))
            await db.commit()
    
    async def add_tap(self, game_id: int, user_id: int, taps: int = 1):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                UPDATE game_players SET taps = taps + ?
                WHERE game_id = ? AND user_id = ?
            ''', (taps, game_id, user_id))
            await db.commit()
    
    async def finish_game(self, game_id: int, results: List[Dict]):
        async with aiosqlite.connect(self.db_path) as db:
            # Обновляем статус игры
            await db.execute('''
                UPDATE games SET status = 'finished', finished_at = CURRENT_TIMESTAMP
                WHERE game_id = ?
            ''', (game_id,))
            
            # Обновляем результаты игроков
            for result in results:
                await db.execute('''
                    UPDATE game_players 
                    SET position = ?, prize = ?
                    WHERE game_id = ? AND user_id = ?
                ''', (result['position'], result['prize'], game_id, result['user_id']))
                
                # Обновляем статистику пользователя
                await db.execute('''
                    UPDATE users 
                    SET total_games = total_games + 1,
                        total_wins = total_wins + ?,
                        total_earned = total_earned + ?
                    WHERE user_id = ?
                ''', (1 if result['position'] <= 5 else 0, result['prize'], result['user_id']))
                
                if result['prize'] > 0:
                    await self.add_transaction(
                        result['user_id'], 
                        "game_win", 
                        result['prize'], 
                        f"Место #{result['position']} в игре #{game_id}"
                    )
            
            await db.commit()
    
    # ========== ТРАНЗАКЦИИ ==========
    
    async def add_transaction(self, user_id: int, tx_type: str, amount: int, description: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT INTO transactions (user_id, type, amount, description)
                VALUES (?, ?, ?, ?)
            ''', (user_id, tx_type, amount, description))
            await db.commit()
    
    # ========== СТАТИСТИКА ==========
    
    async def get_leaderboard(self, limit: int = 10) -> List[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute('''
                SELECT user_id, username, first_name, total_earned, total_wins, total_games
                FROM users
                ORDER BY total_earned DESC
                LIMIT ?
            ''', (limit,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    async def get_admin_stats(self) -> Dict:
        async with aiosqlite.connect(self.db_path) as db:
            stats = {}
            
            # Всего пользователей
            async with db.execute('SELECT COUNT(*) FROM users') as cursor:
                stats['total_users'] = (await cursor.fetchone())[0]
            
            # Новые за 24ч
            async with db.execute('''
                SELECT COUNT(*) FROM users 
                WHERE created_at > datetime('now', '-1 day')
            ''') as cursor:
                stats['new_users_24h'] = (await cursor.fetchone())[0]
            
            # Всего игр
            async with db.execute('SELECT COUNT(*) FROM games') as cursor:
                stats['total_games'] = (await cursor.fetchone())[0]
            
            # Доход (10% с каждой игры)
            async with db.execute('''
                SELECT SUM(prize_pool) FROM games WHERE status = 'finished'
            ''') as cursor:
                total_pool = (await cursor.fetchone())[0] or 0
                stats['total_revenue'] = int(total_pool * 0.1)
            
            return stats