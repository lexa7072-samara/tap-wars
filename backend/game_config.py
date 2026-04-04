# Конфигурация типов игр
GAME_TYPES = {
    "mini": {
        "name": "Мини",
        "emoji": "🟢",
        "ticket_price": 10,
        "max_players": 10,
        "prize_pool": 60,
        "duration": 30,  # секунд
        "prize_distribution": [35, 15, 10],  # топ-3: 1-е место 35⭐, 2-е 15⭐, 3-е 10⭐
        "description": "Быстрая игра для новичков"
    },
    "standard": {
        "name": "Стандарт",
        "emoji": "🔵",
        "ticket_price": 50,
        "max_players": 20,
        "prize_pool": 750,
        "duration": 60,
        "prize_distribution": [300, 200, 120, 80, 50],  # топ-5
        "description": "Классическая битва"
    },
    "vip": {
        "name": "VIP",
        "emoji": "🟣",
        "ticket_price": 100,
        "max_players": 10,
        "prize_pool": 750,
        "duration": 60,
        "prize_distribution": [400, 250, 100],  # топ-3: 1-е место 400⭐, 2-е 250⭐, 3-е 100⭐
        "description": "Элитная игра с большими призами"
    }
}

# Подсчёт дохода
# Мини: 10 игроков × 10⭐ = 100⭐ сбор - 60⭐ призы = 40⭐ доход
# Стандарт: 20 игроков × 50⭐ = 1000⭐ сбор - 750⭐ призы = 250⭐ доход
# VIP: 10 игроков × 100⭐ = 1000⭐ сбор - 750⭐ призы = 250⭐ доход
