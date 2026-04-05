import sqlite3

def reset_database():
    conn = sqlite3.connect('game.db')
    cursor = conn.cursor()
    
    # Список всех таблиц
    tables = ['users', 'user_tickets', 'games', 'game_players', 'winnings', 'withdraw_requests']
    
    for table in tables:
        cursor.execute(f'DELETE FROM {table}')
        print(f'✅ Очищена таблица: {table}')
    
    # Сброс автоинкремента
    cursor.execute('DELETE FROM sqlite_sequence')
    
    conn.commit()
    conn.close()
    print('🎉 База данных полностью очищена!')

if __name__ == '__main__':
    reset_database()
