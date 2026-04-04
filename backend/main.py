import json
import asyncio
import urllib.parse
from typing import Dict, List
from pathlib import Path
from dotenv import load_dotenv
import os

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .admin import router as admin_router
from .database import Database
from .game_engine import GameEngine
from .game_config import GAME_TYPES
from aiogram import Bot
from aiogram.types import LabeledPrice

load_dotenv()

app = FastAPI(title="Tap Wars API")

# Telegram Bot
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://tap-wars.onrender.com")
bot = Bot(token=BOT_TOKEN) if BOT_TOKEN else None

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://tap-wars.onrender.com",
        "https://t.me",
        "https://web.telegram.org",
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin_router)

BASE_DIR = Path(__file__).resolve().parent.parent

if (BASE_DIR / "frontend").exists():
    app.mount("/static", StaticFiles(directory=str(BASE_DIR / "frontend")), name="static")

db = Database()
game_engine = GameEngine(db)
active_connections: Dict[int, List[WebSocket]] = {}

# ========== МОДЕЛИ ==========

class UserAuth(BaseModel):
    init_data: str

class ScoreUpdate(BaseModel):
    user_id: int
    username: str
    full_name: str
    score: int

# ========== ЗАПУСК ==========

@app.on_event("startup")
async def startup():
    await db.init()
    await game_engine.create_new_game("standard")
    print("🚀 Tap Wars API запущен!")

@app.get("/")
async def root():
    index_path = BASE_DIR / "frontend" / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "Tap Wars API is running!", "docs": "/docs", "health": "/health"}

@app.get("/health")
async def health():
    return {"status": "ok"}

# ========== API АВТОРИЗАЦИИ ==========

@app.post("/api/auth")
async def authenticate(auth: UserAuth):
    data = dict(urllib.parse.parse_qsl(auth.init_data))
    user_data = json.loads(data.get('user', '{}'))
    user_id = user_data.get('id')
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid auth data")
    
    await db.add_user(
        user_id=user_id,
        username=user_data.get('username', 'Anonymous'),
        first_name=user_data.get('first_name', 'User'),
        referred_by=None
    )
    
    user = await db.get_user(user_id)
    return {"success": True, "user": user}

# ========== API ИГРЫ ==========

@app.get("/api/game/types")
async def get_game_types():
    return {"types": GAME_TYPES}

@app.post("/api/game/create")
async def create_game(request: Request):
    data = await request.json()
    game_type = data.get("game_type", "standard")
    game_id = await game_engine.create_new_game(game_type)
    return {"success": True, "game_id": game_id}

@app.get("/api/game/current")
async def get_current_game():
    game = await db.get_active_game()
    if not game:
        game_id = await game_engine.create_new_game("standard")
        game = await db.get_active_game()
    
    players_count = await db.get_game_players_count(game["game_id"])
    
    return {
        "game_id": game["game_id"],
        "game_type": game.get("game_type", "standard"),
        "players_count": players_count,
        "max_players": game["max_players"],
        "ticket_price": game["ticket_price"],
        "prize_pool": game["prize_pool"],
        "duration": game.get("duration", 60),
        "status": game["status"]
    }

@app.post("/api/game/{game_id}/join")
async def join_game(game_id: int, user_id: int):
    success = await game_engine.join_game(game_id, user_id)
    
    if success:
        players_count = await db.get_game_players_count(game_id)
        
        await broadcast_to_game(game_id, {
            "type": "player_joined",
            "players_count": players_count
        })
        
        if await game_engine.check_game_start(game_id):
            await broadcast_to_game(game_id, {
                "type": "game_starting",
                "countdown": 3
            })
            await asyncio.sleep(3)
            await broadcast_to_game(game_id, {"type": "game_started"})
        
        return {"success": True, "players_count": players_count}
    
    return {"success": False, "error": "Already in game or no ticket"}

# ========== API ОБНОВЛЕНИЯ СЧЁТА ==========

@app.post("/api/update-score")
async def update_score(data: ScoreUpdate):
    await db.update_user_score(data.user_id, data.username, data.full_name, data.score)
    leaders = await db.get_leaderboard(10)
    return {"success": True, "leaderboard": leaders}

@app.get("/api/leaderboard")
async def get_leaderboard():
    leaders = await db.get_leaderboard(10)
    return {"leaders": leaders}

@app.get("/api/balance/{user_id}")
async def get_balance(user_id: int):
    user = await db.get_user(user_id)
    if user:
        return {"success": True, "balance": user.get("balance", 0)}
    return {"success": False, "balance": 0}

# ========== API ВЫВОДА СРЕДСТВ ==========

@app.post("/api/withdraw/request")
async def request_withdraw(request: Request):
    data = await request.json()
    user_id = data.get("user_id")
    amount = data.get("amount")
    
    MIN_WITHDRAW = 100
    
    if amount < MIN_WITHDRAW:
        return {
            "success": False, 
            "error": f"Минимальная сумма вывода: {MIN_WITHDRAW} ⭐"
        }
    
    user = await db.get_user(user_id)
    if not user or user.get("balance", 0) < amount:
        return {"success": False, "error": "Недостаточно звезд"}
    
    success = await db.withdraw_stars(user_id, amount)
    
    if success:
        return {
            "success": True,
            "message": f"Запрос на вывод {amount} ⭐ создан. Ожидайте обработки."
        }
    
    return {"success": False, "error": "Ошибка при создании запроса"}

@app.get("/api/withdraw/history/{user_id}")
async def get_withdraw_history(user_id: int):
    history = await db.get_withdraw_history(user_id)
    return {"success": True, "history": history}

@app.get("/api/withdraw/info/{user_id}")
async def get_withdraw_info(user_id: int):
    info = await db.get_withdraw_info(user_id)
    return {
        "min_amount": 100,
        "fee": 0,
        "pending": info.get("pending", 0)
    }

# ========== API ПЛАТЕЖЕЙ ==========

@app.post("/api/payment/create-invoice")
async def create_invoice(request: Request):
    try:
        data = await request.json()
        user_id = data.get("user_id")
        game_id = data.get("game_id")
        amount = data.get("amount", 50)
        
        if not bot:
            return {"success": False, "error": "Bot not initialized"}
        
        invoice_link = await bot.create_invoice_link(
            title="🎮 Билет на Tap Wars",
            description=f"Участие в битве на игроков. Топ-делят призовой фонд",
            payload=f"game_ticket_{game_id}_{user_id}",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label="Билет на игру", amount=amount)]
        )
        
        # Добавляем билет пользователю после оплаты
        game = await db.get_active_game()
        if game:
            await db.add_ticket(user_id, game.get("game_type", "standard"), 1)
        
        return {"success": True, "invoice_link": invoice_link}
    except Exception as e:
        print(f"Error creating invoice: {e}")
        return {"success": False, "error": str(e)}

# ========== ВЕБХУК ДЛЯ TELEGRAM ==========

@app.post("/webhook")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        
        if "pre_checkout_query" in data:
            query_id = data["pre_checkout_query"]["id"]
            if bot:
                await bot.answer_pre_checkout_query(query_id, ok=True)
            return {"ok": True}
        
        if "message" in data and "successful_payment" in data["message"]:
            payment = data["message"]["successful_payment"]
            payload = payment["invoice_payload"]
            
            parts = payload.split("_")
            if len(parts) >= 4:
                game_id = int(parts[2])
                user_id = int(parts[3])
                
                await game_engine.join_game(game_id, user_id)
                print(f"✅ User {user_id} joined game {game_id} after payment")
        
        return {"ok": True}
    except Exception as e:
        print(f"Webhook error: {e}")
        return {"ok": False}

# ========== WEBSOCKET ==========

@app.websocket("/ws/game/{game_id}/{user_id}")
async def websocket_game(websocket: WebSocket, game_id: int, user_id: int):
    await websocket.accept()
    
    if game_id not in active_connections:
        active_connections[game_id] = []
    active_connections[game_id].append(websocket)
    
    try:
        while True:
            data = await websocket.receive_json()
            
            if data["type"] == "tap":
                multiplier = data.get("multiplier", 1.0)
                taps = await game_engine.add_tap(game_id, user_id, multiplier)
                
                await websocket.send_json({
                    "type": "tap_confirmed",
                    "taps": taps
                })
                
                state = await game_engine.get_game_state(game_id)
                await broadcast_to_game(game_id, {
                    "type": "leaderboard_update",
                    "leaderboard": state["leaderboard"]
                })
    
    except WebSocketDisconnect:
        if game_id in active_connections and websocket in active_connections[game_id]:
            active_connections[game_id].remove(websocket)
            if not active_connections[game_id]:
                del active_connections[game_id]

async def broadcast_to_game(game_id: int, message: dict):
    if game_id not in active_connections:
        return
    
    disconnected = []
    for ws in active_connections[game_id]:
        try:
            await ws.send_json(message)
        except:
            disconnected.append(ws)
    
    for ws in disconnected:
        if ws in active_connections[game_id]:
            active_connections[game_id].remove(ws)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
