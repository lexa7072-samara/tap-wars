import asyncio
import random
from typing import Dict, List, Optional
from datetime import datetime

class GameEngine:
    def __init__(self, db):
        self.db = db
        self.active_games = {}  # {game_id: game_state}
        self.taps_buffer = {}   # {game_id: {user_id: taps}}
        
    async def create_new_game(self) -> int:
        """Создать новую игру"""
        game_id = await self.db.create_game(
            status="waiting",
            max_players=50,
            ticket_price=50,
            prize_pool=2000,
            start_time=None,
            end_time=None
        )
        
        self.active_games[game_id] = {
            "status": "waiting",
            "players": [],
            "taps": {},
            "start_time": None,
            "end_time": None
        }
        
        return game_id
    
    async def join_game(self, game_id: int, user_id: int) -> bool:
        """Присоединить игрока к игре"""
        if game_id not in self.active_games:
            return False
            
        game = self.active_games[game_id]
        
        if user_id in game["players"]:
            return False
            
        if len(game["players"]) >= 50:
            return False
            
        game["players"].append(user_id)
        game["taps"][user_id] = 0
        
        await self.db.add_player_to_game(game_id, user_id)
        
        return True
    
    async def add_tap(self, game_id: int, user_id: int, multiplier: float = 1.0) -> int:
        """Добавить тап игроку"""
        if game_id not in self.active_games:
            return 0
            
        game = self.active_games[game_id]
        
        if user_id not in game["taps"]:
            return 0
            
        taps_added = int(1 * multiplier)
        game["taps"][user_id] += taps_added
        
        await self.db.update_player_taps(game_id, user_id, game["taps"][user_id])
        
        return game["taps"][user_id]
    
    async def check_game_start(self, game_id: int) -> bool:
        """Проверить, нужно ли начать игру"""
        if game_id not in self.active_games:
            return False
            
        game = self.active_games[game_id]
        
        if len(game["players"]) >= 50 and game["status"] == "waiting":
            await self.start_game(game_id)
            return True
            
        return False
    
    async def start_game(self, game_id: int):
        """Начать игру"""
        if game_id not in self.active_games:
            return
            
        game = self.active_games[game_id]
        game["status"] = "active"
        game["start_time"] = datetime.now()
        
        await self.db.update_game_status(game_id, "active")
        
        # Запустить таймер на 60 секунд
        asyncio.create_task(self.end_game_countdown(game_id))
    
    async def end_game_countdown(self, game_id: int):
        """Обратный отсчет до конца игры"""
        await asyncio.sleep(60)  # 60 секунд игра
        
        await self.end_game(game_id)
    
    async def end_game(self, game_id: int):
        """Завершить игру и начислить призы"""
        if game_id not in self.active_games:
            return
            
        game = self.active_games[game_id]
        game["status"] = "ended"
        game["end_time"] = datetime.now()
        
        # Получить топ-5 игроков
        sorted_players = sorted(game["taps"].items(), key=lambda x: x[1], reverse=True)
        top_5 = sorted_players[:5]
        
        # Распределить призы (2000 звезд)
        prizes = [800, 500, 350, 200, 150]  # Сумма = 2000
        
        for i, (user_id, taps) in enumerate(top_5):
            prize = prizes[i] if i < len(prizes) else 0
            await self.db.add_winnings(user_id, prize, game_id)
            await self.db.update_user_balance(user_id, prize)
        
        await self.db.update_game_status(game_id, "ended")
        
        # Очистить активную игру
        del self.active_games[game_id]
        
        # Создать новую игру
        await self.create_new_game()
    
    async def apply_boost(self, game_id: int, user_id: int, boost_type: str) -> bool:
        """Применить буст"""
        # Простая реализация бустов
        boosts = {
            "double_tap": {"multiplier": 2.0, "duration": 10},
            "triple_tap": {"multiplier": 3.0, "duration": 5},
            "auto_tap": {"multiplier": 0.5, "duration": 30}
        }
        
        if boost_type not in boosts:
            return False
            
        # Проверить, есть ли у пользователя буст
        has_boost = await self.db.check_user_boost(user_id, boost_type)
        
        if not has_boost:
            return False
            
        # Активировать буст
        await self.db.use_boost(user_id, boost_type)
        
        return True
    
    async def get_game_state(self, game_id: int) -> Dict:
        """Получить текущее состояние игры"""
        if game_id not in self.active_games:
            return {}
            
        game = self.active_games[game_id]
        
        # Сортировка лидерборда
        leaderboard = sorted(
            [{"user_id": uid, "taps": taps} for uid, taps in game["taps"].items()],
            key=lambda x: x["taps"],
            reverse=True
        )[:10]  # Топ-10
        
        return {
            "status": game["status"],
            "players_count": len(game["players"]),
            "leaderboard": leaderboard,
            "time_left": 60 - (datetime.now() - game["start_time"]).seconds if game["start_time"] else 60
        }