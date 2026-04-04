// ========== TELEGRAM WEB APP INIT ==========

const tg = window.Telegram.WebApp;
tg.expand();
tg.enableClosingConfirmation();

// Настройка темы
tg.setHeaderColor('#667eea');
tg.setBackgroundColor('#667eea');

// ========== ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ==========

const API_URL = 'https://your-backend.com';  // Замени на свой URL
let ws = null;
let currentUser = null;
let currentGame = null;
let tapCount = 0;
let currentMultiplier = 1.0;
let gameTimer = null;

// ========== ИНИЦИАЛИЗАЦИЯ ==========

async function init() {
    try {
        showScreen('loading-screen');
        
        // Авторизация через Telegram
        const initData = tg.initData;
        
        const response = await fetch(`${API_URL}/api/auth`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ init_data: initData })
        });
        
        const data = await response.json();
        
        if (data.success) {
            currentUser = data.user;
            updateUserInfo();
            showScreen('menu-screen');
        } else {
            throw new Error('Auth failed');
        }
    } catch (error) {
        console.error('Init error:', error);
        tg.showAlert('Ошибка загрузки. Перезапустите приложение.');
    }
}

// ========== UI ФУНКЦИИ ==========

function showScreen(screenId) {
    document.querySelectorAll('.screen').forEach(screen => {
        screen.classList.remove('active');
    });
    document.getElementById(screenId).classList.add('active');
}

function updateUserInfo() {
    document.getElementById('username').textContent = currentUser.first_name;
    document.getElementById('balance').textContent = `${currentUser.total_earned || 0} ⭐`;
}

// ========== ГЛАВНОЕ МЕНЮ ==========

async function startGame() {
    try {
        // Получаем текущую игру
        const response = await fetch(`${API_URL}/api/game/current`);
        const gameData = await response.json();
        
        currentGame = gameData;
        
        // Показываем лобби
        showLobby();
        
    } catch (error) {
        console.error('Start game error:', error);
        tg.showAlert('Не удалось загрузить игру');
    }
}

function showLobby() {
    showScreen('lobby-screen');
    updateLobbyInfo();
    
    // Опции покупки билета
    const buttons = [
        {
            text: '💳 Купить билет (50 ⭐)',
            callback: () => buyTicket()
        }
    ];
    
    if (currentUser.free_tickets > 0) {
        buttons.unshift({
            text: `🎟 Играть бесплатно (${currentUser.free_tickets} билет${currentUser.free_tickets > 1 ? 'а' : ''})`,
            callback: () => joinGameFree()
        });
    }
    
    tg.MainButton.setText(buttons[0].text);
    tg.MainButton.onClick(buttons[0].callback);
    tg.MainButton.show();
    
    tg.BackButton.onClick(() => {
        leaveLobby();
    });
    tg.BackButton.show();
}

function updateLobbyInfo() {
    const playersText = `${currentGame.players_count} / ${currentGame.players_needed}`;
    const prizePool = currentGame.players_count * currentGame.ticket_price;
    
    document.getElementById('lobby-players').textContent = playersText;
    document.getElementById('prize-pool').textContent = `${prizePool} ⭐`;
    
    // Обновляем каждые 2 секунды
    setTimeout(async () => {
        if (document.getElementById('lobby-screen').classList.contains('active')) {
            const response = await fetch(`${API_URL}/api/game/current`);
            const gameData = await response.json();
            currentGame = gameData;
            updateLobbyInfo();
        }
    }, 2000);
}

async function buyTicket() {
    try {
        // Создаем инвойс
        const response = await fetch(`${API_URL}/api/payment/invoice`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                user_id: currentUser.user_id,
                game_id: currentGame.game_id
            })
        });
        
        const data = await response.json();
        
        // Открываем инвойс через Telegram
        tg.openInvoice(data.invoice_url, (status) => {
            if (status === 'paid') {
                joinGame();
            }
        });
        
    } catch (error) {
        console.error('Buy ticket error:', error);
        tg.showAlert('Ошибка оплаты');
    }
}

async function joinGameFree() {
    await joinGame();
}

async function joinGame() {
    try {
        const response = await fetch(`${API_URL}/api/game/${currentGame.game_id}/join?user_id=${currentUser.user_id}`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            tg.showPopup({
                title: '✅ Успешно!',
                message: 'Ты в игре! Ожидай начала...',
                buttons: [{type: 'ok'}]
            });
            
            // Подключаемся к WebSocket
            connectToGame();
        } else {
            tg.showAlert(data.error || 'Не удалось присоединиться');
        }
        
    } catch (error) {
        console.error('Join game error:', error);
        tg.showAlert('Ошибка подключения к игре');
    }
}

function leaveLobby() {
    tg.MainButton.hide();
    tg.BackButton.hide();
    backToMenu();
}

function backToMenu() {
    if (ws) {
        ws.close();
        ws = null;
    }
    showScreen('menu-screen');
}

// ========== WEBSOCKET ==========

function connectToGame() {
    const wsUrl = `${API_URL.replace('https', 'wss').replace('http', 'ws')}/ws/game/${currentGame.game_id}/${currentUser.user_id}`;
    
    ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
        console.log('WebSocket connected');
    };
    
    ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        handleWebSocketMessage(message);
    };
    
    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        tg.showAlert('Потеряно соединение с игрой');
    };
    
    ws.onclose = () => {
        console.log('WebSocket closed');
    };
}

function handleWebSocketMessage(message) {
    switch (message.type) {
        case 'player_joined':
            currentGame.players_count = message.players_count;
            updateLobbyInfo();
            break;
            
        case 'game_starting':
            showCountdown(message.countdown);
            break;
            
        case 'game_started':
            startGameplay();
            break;
            
        case 'tap_confirmed':
            handleTapConfirmed(message.taps);
            break;
            
        case 'leaderboard_update':
            updateMiniLeaderboard(message.leaderboard);
            break;
            
        case 'game_finished':
            showResults(message.results);
            break;
            
        case 'boost_activated':
            handleBoostActivated(message);
            break;
    }
}

// ========== COUNTDOWN ==========

function showCountdown(seconds) {
    tg.MainButton.hide();
    tg.BackButton.hide();
    
    let count = seconds;
    const countdownInterval = setInterval(() => {
        tg.showPopup({
            title: '🎮 Игра начинается!',
            message: `${count}...`,
            buttons: []
        });
        
        count--;
        
        if (count < 0) {
            clearInterval(countdownInterval);
            tg.closePopup();
        }
    }, 1000);
}

// ========== LEADERBOARD ==========

async function showLeaderboard() {
    try {
        const response = await fetch(`${API_URL}/api/leaderboard`);
        const data = await response.json();
        
        let html = '<div class="leaderboard-list">';
        const medals = ['🥇', '🥈', '🥉'];
        
        data.leaders.forEach((leader, index) => {
            const medal = index < 3 ? medals[index] : `${index + 1}.`;
            html += `
                <div class="leader-item">
                    <span class="leader-position">${medal}</span>
                    <span class="leader-name">${leader.first_name}</span>
                    <span class="leader-stats">${leader.total_earned} ⭐</span>
                </div>
            `;
        });
        
        html += '</div>';
        
        // Показываем в попапе или новом экране
        tg.showPopup({
            title: '🏆 ТОП-100 ИГРОКОВ',
            message: html,
            buttons: [{type: 'close'}]
        });
        
    } catch (error) {
        console.error('Leaderboard error:', error);
    }
}

// ========== PROFILE ==========

async function showProfile() {
    try {
        const response = await fetch(`${API_URL}/api/user/${currentUser.user_id}`);
        const userData = await response.json();
        
        const winRate = userData.total_games > 0 
            ? Math.round((userData.total_wins / userData.total_games) * 100) 
            : 0;
        
        tg.showPopup({
            title: '👤 Твой профиль',
            message: `
                📊 Игр сыграно: ${userData.total_games}
                🏆 Побед: ${userData.total_wins} (${winRate}%)
                💰 Всего выиграно: ${userData.total_earned} ⭐
                
                👥 Рефералов: ${userData.referrals}
                🎟 Бесплатных билетов: ${userData.free_tickets}
                
                💎 Бонус к тапам: +${userData.referrals * 5}%
            `,
            buttons: [{type: 'close'}]
        });
        
    } catch (error) {
        console.error('Profile error:', error);
    }
}

// ========== REFERRALS ==========

function showReferrals() {
    const botUsername = 'YourBotUsername';  // Замени на имя своего бота
    const refLink = `https://t.me/${botUsername}?start=ref${currentUser.user_id}`;
    
    const message = `
👥 Приглашай друзей и получай бонусы!

🎁 За каждого друга:
• +25 ⭐ на баланс
• +5% к силе тапов навсегда
• +1 бесплатный билет (каждые 3 реферала)

Твоих рефералов: ${currentUser.referrals}
    `;
    
    tg.showPopup({
        title: '🚀 Пригласи друзей',
        message: message,
        buttons: [
            {
                type: 'default',
                text: 'Поделиться ссылкой'
            },
            {type: 'close'}
        ]
    }, (buttonId) => {
        if (buttonId === 'default') {
            tg.openTelegramLink(`https://t.me/share/url?url=${encodeURIComponent(refLink)}&text=${encodeURIComponent('🎮 Играй в Tap Wars и выигрывай реальные призы!')}`);
        }
    });
}

// ========== ЗАПУСК ПРИ ЗАГРУЗКЕ ==========

document.addEventListener('DOMContentLoaded', () => {
    init();
});

// Обработка закрытия приложения
window.addEventListener('beforeunload', () => {
    if (ws) {
        ws.close();
    }
});