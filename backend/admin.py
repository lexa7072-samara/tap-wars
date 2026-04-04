from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import List, Dict
import os

router = APIRouter(prefix="/admin", tags=["Admin"])

# Простой пароль для админки (лучше хранить в .env)
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

class WithdrawAction(BaseModel):
    request_id: int
    action: str  # "approve" or "reject"

class WithdrawRequest(BaseModel):
    request_id: int
    user_id: int
    amount: int
    status: str
    created_at: str

def check_auth(password: str):
    return password == ADMIN_PASSWORD

@router.post("/auth")
async def admin_auth(request: Request):
    data = await request.json()
    password = data.get("password")
    if check_auth(password):
        return {"success": True, "token": "admin_authenticated"}
    return {"success": False, "error": "Неверный пароль"}

@router.get("/withdraw/requests")
async def get_withdraw_requests(password: str):
    if not check_auth(password):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    from .database import Database
    db = Database()
    await db.init()
    
    cursor = db.connection.cursor()
    cursor.execute('''
        SELECT w.id, w.user_id, w.amount, w.status, w.created_at, u.username, u.full_name
        FROM withdraw_requests w
        JOIN users u ON w.user_id = u.user_id
        WHERE w.status = 'pending'
        ORDER BY w.created_at DESC
    ''')
    rows = cursor.fetchall()
    
    return {
        "requests": [{
            "id": r[0],
            "user_id": r[1],
            "amount": r[2],
            "status": r[3],
            "created_at": r[4],
            "username": r[5],
            "full_name": r[6]
        } for r in rows]
    }

@router.post("/withdraw/action")
async def withdraw_action(request: Request):
    data = await request.json()
    password = data.get("password")
    request_id = data.get("request_id")
    action = data.get("action")
    
    if not check_auth(password):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    from .database import Database
    db = Database()
    await db.init()
    
    cursor = db.connection.cursor()
    
    if action == "approve":
        cursor.execute('''
            UPDATE withdraw_requests 
            SET status = 'completed', completed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (request_id,))
        db.connection.commit()
        return {"success": True, "message": "Запрос одобрен"}
    
    elif action == "reject":
        cursor.execute('''
            UPDATE withdraw_requests 
            SET status = 'cancelled'
            WHERE id = ?
        ''', (request_id,))
        
        # Возвращаем звезды пользователю
        cursor.execute('SELECT user_id, amount FROM withdraw_requests WHERE id = ?', (request_id,))
        row = cursor.fetchone()
        if row:
            cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (row[1], row[0]))
        
        db.connection.commit()
        return {"success": True, "message": "Запрос отклонён"}
    
    return {"success": False, "error": "Неизвестное действие"}

@router.get("/stats")
async def get_stats(password: str):
    if not check_auth(password):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    from .database import Database
    db = Database()
    await db.init()
    
    cursor = db.connection.cursor()
    
    # Общая статистика
    cursor.execute('SELECT COUNT(*) FROM users')
    total_users = cursor.fetchone()[0]
    
    cursor.execute('SELECT SUM(balance) FROM users')
    total_balance = cursor.fetchone()[0] or 0
    
    cursor.execute('SELECT SUM(total_score) FROM users')
    total_taps = cursor.fetchone()[0] or 0
    
    cursor.execute('SELECT SUM(amount) FROM winnings WHERE claimed = 0')
    total_winnings = cursor.fetchone()[0] or 0
    
    cursor.execute('SELECT SUM(amount) FROM withdraw_requests WHERE status = "pending"')
    pending_withdraw = cursor.fetchone()[0] or 0
    
    cursor.execute('SELECT SUM(amount) FROM withdraw_requests WHERE status = "completed"')
    completed_withdraw = cursor.fetchone()[0] or 0
    
    # Статистика по играм
    cursor.execute('''
        SELECT game_type, COUNT(*) FROM games GROUP BY game_type
    ''')
    games_by_type = {row[0]: row[1] for row in cursor.fetchall()}
    
    # Топ игроков по выигрышам
    cursor.execute('''
        SELECT u.full_name, u.username, SUM(w.amount) as total
        FROM winnings w
        JOIN users u ON w.user_id = u.user_id
        WHERE w.claimed = 0
        GROUP BY w.user_id
        ORDER BY total DESC
        LIMIT 10
    ''')
    top_winners = [{"name": r[0] or r[1], "amount": r[2]} for r in cursor.fetchall()]
    
    return {
        "total_users": total_users,
        "total_balance": total_balance,
        "total_taps": total_taps,
        "total_winnings": total_winnings,
        "pending_withdraw": pending_withdraw,
        "completed_withdraw": completed_withdraw,
        "games_by_type": games_by_type,
        "top_winners": top_winners
    }

@router.get("/users")
async def get_users(password: str, limit: int = 50, offset: int = 0):
    if not check_auth(password):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    from .database import Database
    db = Database()
    await db.init()
    
    cursor = db.connection.cursor()
    cursor.execute('''
        SELECT user_id, username, full_name, balance, total_score, games_played, created_at
        FROM users
        ORDER BY total_score DESC
        LIMIT ? OFFSET ?
    ''', (limit, offset))
    rows = cursor.fetchall()
    
    return {
        "users": [{
            "user_id": r[0],
            "username": r[1],
            "full_name": r[2],
            "balance": r[3],
            "total_score": r[4],
            "games_played": r[5],
            "created_at": r[6]
        } for r in rows]
    }