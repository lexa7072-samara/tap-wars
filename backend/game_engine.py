import asyncio
from datetime import datetime
from typing import Dict, List
from config import GAME_CONFIG
from database import Database

class GameEngine:
    def __init__(self, db: Database):
        self.db = db
        self.active_games: Dict[int, Dict] = {}  # {game_id: {players, taps, boosts}}
        self.game_tasks: Dict[int, asyncio.Task] = {}
    
    async def create_new_game(self) -> int:
        """Создать новую игру"""
        game_id = await self.db.create_game(
            ticket_price=GAME_CONFIG["TICKET_PRICE"],
            players_needed=GAME_CONFIG["PLAYERS_NEEDED"]
        )
        self.active_games[game_id] = {
            "players": {},
            "taps": {},
            "boosts": {},
            "started": False
        }
        return game_id
    
    async def join_game(self, game_id: int, user_id: int) -> bool:
        """Присоединиться к игре"""
        success = await self.db.join_game(game_id, user_id)
        if success:
            if game_id not in self.active_games:
                self.active_games[game_id] = {
                    "players": {},
                    "taps": {},
                    "boosts": {},
                    "started": False
                }
            self.active_games[game_id]["players"][user_id] = {
                "taps": 0,
                "multiplier": 1.0,
                "boost_expires": None
            }
        return success
    
    async def check_game_start(self, game_id: int) -> bool:
        """Проверить готовность к старту"""
        players_count = await self.db.get_game_players_count(game_id)
        if players_count >= GAME_CONFIG["PLAYERS_NEEDED"]:
            await self.start_game(game_id)
            return True
        return False
    
    async def start_game(self, game_id: int):
        """Запустить игру"""
        await self.db.start_game(game_id)
        self.active_games[game_id]["started"] = True
        
        # Запускаем таймер игры
        task = asyncio.create_task(self.game_timer(game_id))
        self.game_tasks[game_id] = task
    
    async def game_timer(self, game_id: int):
        """Таймер игры (60 секунд)"""
        duration = GAME_CONFIG["GAME_DURATION"]
        
        # Отправляем уведомления каждые 10 секунд
        for elapsed in range(0, duration, 10):
            await asyncio.sleep(10)
            remaining = duration - elapsed - 10
            if remaining > 0:
                # Здесь можно отправлять уведомления игрокам
                pass
        
        # Игра закончилась
        await self.finish_game(game_id)
    
    async def add_tap(self, game_id: int, user_id: int, multiplier: float = 1.0) -> int:
        """Добавить тап"""
        if game_id not in self.active_games or not self.active_games[game_id]["started"]:
            return 0
        
        if user_id not in self.active_games[game_id]["players"]:
            return 0
        
        # Проверяем активные бусты
        player = self.active_games[game_id]["players"][user_id]
        current_multiplier = player.get("multiplier", 1.0)
        
        # Проверяем истечение буста
        if player.get("boost_expires") and datetime.now() > player["boost_expires"]:
            player["multiplier"] = 1.0
            player["boost_expires"] = None
            current_multiplier = 1.0
        
        # Бонус от рефералов
        user = await self.db.get_user(user_id)
        referral_bonus = 1 + (user["referrals"] * GAME_CONFIG["REFERRAL_TAP_BONUS"])
        
        # Итоговый множитель
        total_multiplier = current_multiplier * multiplier * referral_bonus
        taps = int(1 * total_multiplier)
        
        # Обновляем счётчик
        player["taps"] += taps
        await self.db.add_tap(game_id, user_id, taps)
        
        return taps
    
    async def apply_boost(self, game_id: int, user_id: int, boost_type: str) -> bool:
        """Применить буст"""
        if game_id not in self.active_games or not self.active_games[game_id]["started"]:
            return False
        
        if user_id not in self.active_games[game_id]["players"]:
            return False
        
        player = self.active_games[game_id]["players"][user_id]
        
        if boost_type == "2x":
            player["multiplier"] = 2.0
            duration = 30
        elif boost_type == "3x":
            player["multiplier"] = 3.0
            duration = 30
        elif boost_type == "turbo":
            player["multiplier"] = 5.0
            duration = 10
        else:
            return False
        
        from datetime import timedelta
        player["boost_expires"] = datetime.now() + timedelta(seconds=duration)
        
        return True
    
    async def finish_game(self, game_id: int):
        """Завершить игру и подсчитать результаты"""
        players = await self.db.get_game_players(game_id)
        
        # Сортируем по тапам
        players.sort(key=lambda x: x["taps"], reverse=True)
        
        # Подсчитываем призовой фонд
        ticket_price = GAME_CONFIG["TICKET_PRICE"]
        total_pool = len(players) * ticket_price
        prize_pool = int(total_pool * GAME_CONFIG["PRIZE_POOL_PERCENT"] / 100)
        
        # Распределяем призы
        results = []
        for position, player in enumerate(players, start=1):
            prize = 0
            if position <= 5:
                prize_percent = GAME_CONFIG["PRIZES"].get(position, 0)
                prize = int(prize_pool * prize_percent)
            
            results.append({
                "user_id": player["user_id"],
                "position": position,
                "taps": player["taps"],
                "prize": prize
            })
        
        # Сохраняем результаты
        await self.db.finish_game(game_id, results)
        
        # Очищаем из памяти
        if game_id in self.active_games:
            del self.active_games[game_id]
        if game_id in self.game_tasks:
            del self.game_tasks[game_id]
        
        return results
    
    async def get_game_state(self, game_id: int) -> Dict:
        """Получить текущее состояние игры"""
        if game_id not in self.active_games:
            return None
        
        game = self.active_games[game_id]
        players = await self.db.get_game_players(game_id)
        
        # Сортируем по тапам
        leaderboard = sorted(
            [(p["user_id"], p["username"], p["taps"]) for p in players],
            key=lambda x: x[2],
            reverse=True
        )
        
        return {
            "game_id": game_id,
            "started": game["started"],
            "players_count": len(players),
            "leaderboard": leaderboard[:10]  # Топ-10
        }