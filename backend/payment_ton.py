import hashlib
import hmac
import json
from typing import Dict
from fastapi import HTTPException

class TONPayment:
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
    
    def verify_ton_payment(self, payload: Dict) -> bool:
        """Проверка подписи TON платежа"""
        # Здесь будет логика проверки транзакции в блокчейне TON
        # В реальном проекте нужно проверять через TON Center API
        return True
    
    async def add_ticket_on_ton_payment(self, user_id: int, game_id: int, game_type: str, tx_hash: str):
        """Обработка успешного TON платежа"""
        from .database import Database
        db = Database()
        await db.init()
        
        # Добавляем билет пользователю
        await db.add_ticket(user_id, game_type, 1)
        print(f"✅ User {user_id} bought ticket for {game_type} game via TON")
        
        # Присоединяем к игре
        from .game_engine import GameEngine
        game_engine = GameEngine(db)
        success = await game_engine.join_game(game_id, user_id)
        
        return success
