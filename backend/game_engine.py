import asyncio
from typing import Dict, List
from datetime import datetime
from .game_config import GAME_TYPES

class GameEngine:
    def __init__(self, db):
        self.db = db
        self.active_games = {}
        
    async def create_new_game(self, game_type: str = "standard") -> int:
        config = GAME_TYPES.get(game_type, GAME_TYPES["standard"])
        
        game_id = await self.db.create_game(
            game_type=game_type,
            status="waiting",
            max_players=config["max_players"],
            ticket_price=config["ticket_price"],
            prize_pool=config["prize_pool"],
            duration=config["duration"],
            start_time=None,
            end_time=None
        )
        
        self.active_games[game_id] = {
            "game_type": game_type,
            "config": config,
            "status": "waiting",
            "players": [],
            "taps": {},
            "start_time": None,
            "end_time": None,
            "duration": config["duration"]
        }
        
        return game_id
    
    async def join_game(self, game_id: int, user_id: int) -> bool:
        if game_id not in self.active_games:
            return False
            
        game = self.active_games[game_id]
        
        if user_id in game["players"]:
            return False
            
        if len(game["players"]) >= game["config"]["max_players"]:
            return False
            
        has_ticket = await self.db.check_user_ticket(user_id, game["game_type"])
        if not has_ticket:
            return False
            
        game["players"].append(user_id)
        game["taps"][user_id] = 0
        
        await self.db.use_ticket(user_id, game["game_type"])
        await self.db.add_player_to_game(game_id, user_id)
        
        # Для дуэли: если 2 игрока, сразу запускаем игру
        if game["game_type"] == "duel" and len(game["players"]) >= 2:
            await self.start_game(game_id)
        
        return True
    
    async def add_tap(self, game_id: int, user_id: int, multiplier: float = 1.0) -> int:
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
        if game_id not in self.active_games:
            return False
            
        game = self.active_games[game_id]
        
        if len(game["players"]) >= game["config"]["max_players"] and game["status"] == "waiting":
            await self.start_game(game_id)
            return True
            
        return False
    
    async def start_game(self, game_id: int):
        if game_id not in self.active_games:
            return
            
        game = self.active_games[game_id]
        game["status"] = "active"
        game["start_time"] = datetime.now()
        
        await self.db.update_game_status(game_id, "active")
        
        asyncio.create_task(self.end_game_countdown(game_id))
    
    async def end_game_countdown(self, game_id: int):
        if game_id not in self.active_games:
            return
            
        game = self.active_games[game_id]
        duration = game["duration"]
        
        await asyncio.sleep(duration)
        await self.end_game(game_id)
    
    async def end_game(self, game_id: int):
        if game_id not in self.active_games:
            return
            
        game = self.active_games[game_id]
        game["status"] = "ended"
        game["end_time"] = datetime.now()
        
        sorted_players = sorted(game["taps"].items(), key=lambda x: x[1], reverse=True)
        prize_distribution = game["config"]["prize_distribution"]
        top_count = len(prize_distribution)
        top_players = sorted_players[:top_count]
        
        for i, (user_id, taps) in enumerate(top_players):
            prize = prize_distribution[i] if i < len(prize_distribution) else 0
            await self.db.add_winnings(user_id, prize, game_id)
        
        await self.db.update_game_status(game_id, "ended")
        
        del self.active_games[game_id]
        
        await self.create_new_game(game["game_type"])
    
    async def get_game_state(self, game_id: int) -> Dict:
        if game_id not in self.active_games:
            return {}
            
        game = self.active_games[game_id]
        
        leaderboard = sorted(
            [{"user_id": uid, "taps": taps} for uid, taps in game["taps"].items()],
            key=lambda x: x["taps"],
            reverse=True
        )[:10]
        
        time_elapsed = (datetime.now() - game["start_time"]).seconds if game["start_time"] else 0
        time_left = max(0, game["duration"] - time_elapsed)
        
        return {
            "game_type": game["game_type"],
            "status": game["status"],
            "players_count": len(game["players"]),
            "max_players": game["config"]["max_players"],
            "leaderboard": leaderboard,
            "time_left": time_left,
            "duration": game["duration"],
            "ticket_price": game["config"]["ticket_price"],
            "prize_pool": game["config"]["prize_pool"]
        }
