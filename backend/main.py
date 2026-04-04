import json
import asyncio
import urllib.parse
from typing import Dict, List
from pathlib import Path
from dotenv import load_dotenv

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .database import Database
from .game_engine import GameEngine

load_dotenv()

app = FastAPI(title="Tap Wars API")

# CORS — разрешаем запросы с фронтенда
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://твой-username.github.io",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://*.t.me",  # Для Telegram Mini App
        "https://t.me"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем статические файлы (frontend)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "frontend")), name="static")

# Инициализация
db = Database()
game_engine = GameEngine(db)
active_connections: Dict[int, List[WebSocket]] = {}

# ========== МОДЕЛИ ==========

class UserAuth(BaseModel):
    init_data: str

# ========== ИНИЦИАЛИЗАЦИЯ ==========

@app.on_event("startup")
async def startup():
    await db.init()
    await game_engine.create_new_game()
    print("🚀 Tap Wars API запущен!")

# ========== REST API ==========

@app.post("/api/auth")
async def authenticate(auth: UserAuth):
    """Авторизация через Telegram WebApp"""
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
    
    return {
        "success": True,
        "user": user,
        "token": f"token_{user_id}"
    }

@app.get("/api/game/current")
async def get_current_game():
    """Получить текущую игру"""
    game = await db.get_active_game()
    if not game:
        game_id = await game_engine.create_new_game()
        game = await db.get_active_game()
    
    players_count = await db.get_game_players_count(game["game_id"])
    
    return {
        "game_id": game["game_id"],
        "players_count": players_count,
        "players_needed": 50,
        "ticket_price": 50,
        "status": game["status"]
    }

@app.post("/api/game/{game_id}/join")
async def join_game(game_id: int, user_id: int):
    """Присоединиться к игре"""
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
    
    return {"success": False, "error": "Already in game"}

@app.get("/api/leaderboard")
async def get_leaderboard():
    """Топ игроков"""
    leaders = await db.get_leaderboard(100)
    return {"leaders": leaders}

@app.get("/api/user/{user_id}")
async def get_user_data(user_id: int):
    """Данные пользователя"""
    user = await db.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

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
            
            elif data["type"] == "boost":
                boost_type = data.get("boost_type")
                success = await game_engine.apply_boost(game_id, user_id, boost_type)
                
                await websocket.send_json({
                    "type": "boost_activated",
                    "success": success,
                    "boost_type": boost_type
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

# ========== ПЛАТЕЖИ ==========

@app.post("/api/payment/invoice")
async def create_invoice(user_id: int, game_id: int):
    return {
        "invoice_url": f"https://t.me/$YourBotUsername?start=pay_{game_id}_{user_id}"
    }

# ========== HEALTH ==========

@app.get("/")
async def root():
    return {
        "message": "Tap Wars API is running!",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)