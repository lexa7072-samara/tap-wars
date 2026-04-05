import asyncio
import os
from datetime import datetime, timedelta
from typing import Dict, List
from aiogram import Bot

class StarStats:
    def __init__(self, bot_token: str):
        self.bot = Bot(token=bot_token)
    
    async def get_transactions(self, limit: int = 50, offset: int = 0) -> Dict:
        """Получить транзакции звезд бота"""
        try:
            result = await self.bot.get_star_transactions(limit=limit, offset=offset)
            return {
                "success": True,
                "transactions": result
            }
        except Exception as e:
            print(f"Error getting star transactions: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_total_earned(self) -> int:
        """Получить общую сумму заработанных звезд"""
        try:
            total = 0
            offset = 0
            limit = 50
            
            while True:
                result = await self.bot.get_star_transactions(limit=limit, offset=offset)
                if not result:
                    break
                
                for tx in result:
                    if tx.get("status") == "successful":
                        total += tx.get("amount", 0)
                
                if len(result) < limit:
                    break
                offset += limit
            
            return total
        except Exception as e:
            print(f"Error calculating total: {e}")
            return 0
    
    async def get_daily_stats(self, days: int = 7) -> Dict:
        """Получить статистику по дням"""
        stats = {}
        today = datetime.now().date()
        
        for i in range(days):
            date = today - timedelta(days=i)
            stats[date.isoformat()] = {
                "income": 0,
                "spent": 0,
                "count": 0
            }
        
        try:
            offset = 0
            limit = 50
            
            while True:
                result = await self.bot.get_star_transactions(limit=limit, offset=offset)
                if not result:
                    break
                
                for tx in result:
                    tx_date = datetime.fromtimestamp(tx.get("date", 0)).date()
                    date_str = tx_date.isoformat()
                    
                    if date_str in stats:
                        amount = tx.get("amount", 0)
                        if amount > 0:
                            stats[date_str]["income"] += amount
                        else:
                            stats[date_str]["spent"] += abs(amount)
                        stats[date_str]["count"] += 1
                
                if len(result) < limit:
                    break
                offset += limit
        except Exception as e:
            print(f"Error getting daily stats: {e}")
        
        return stats
    
    async def get_withdrawable_balance(self) -> int:
        """Получить сумму, доступную для вывода (с учетом 21 дня)"""
        try:
            withdrawable = 0
            offset = 0
            limit = 50
            cutoff_date = datetime.now() - timedelta(days=21)
            
            while True:
                result = await self.bot.get_star_transactions(limit=limit, offset=offset)
                if not result:
                    break
                
                for tx in result:
                    if tx.get("status") == "successful":
                        tx_date = datetime.fromtimestamp(tx.get("date", 0))
                        if tx_date <= cutoff_date:
                            withdrawable += tx.get("amount", 0)
                
                if len(result) < limit:
                    break
                offset += limit
            
            return withdrawable
        except Exception as e:
            print(f"Error calculating withdrawable: {e}")
            return 0
