// ========== ИГРОВОЙ ПРОЦЕСС ==========

let canvas, ctx;
let particles = [];
let animationFrame;

function startGameplay() {
    showScreen('game-screen');
    
    // Инициализация canvas
    canvas = document.getElementById('game-canvas');
    ctx = canvas.getContext('2d');
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    
    // Сброс счетчиков
    tapCount = 0;
    currentMultiplier = 1.0;
    updateTapCounter();
    
    // Запуск таймера
    startTimer(60);
    
    // Запуск анимации
    animate();
    
    // Вибрация при старте
    tg.HapticFeedback.impactOccurred('medium');
    
    // Настройка кнопки тапа
    const tapButton = document.getElementById('tap-button');
    tapButton.addEventListener('touchstart', handleTap);
    tapButton.addEventListener('click', handleTap);
}

// ========== ТАЙМЕР ИГРЫ ==========

function startTimer(seconds) {
    let timeLeft = seconds;
    const timerElement = document.getElementById('game-timer');
    
    gameTimer = setInterval(() => {
        timeLeft--;
        timerElement.textContent = timeLeft;
        
        // Меняем цвет при окончании времени
        if (timeLeft <= 10) {
            timerElement.style.color = '#ff6b6b';
            timerElement.style.animation = 'pulse 0.5s infinite';
        }
        
        if (timeLeft <= 5) {
            tg.HapticFeedback.impactOccurred('heavy');
        }
        
        if (timeLeft <= 0) {
            clearInterval(gameTimer);
            endGame();
        }
    }, 1000);
}

// ========== ТАП МЕХАНИКА ==========

function handleTap(e) {
    e.preventDefault();
    
    // Отправляем тап на сервер через WebSocket
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            type: 'tap',
            multiplier: currentMultiplier
        }));
    }
    
    // Визуальный фидбек
    createParticles(e);
    animateButton();
    
    // Вибрация
    tg.HapticFeedback.impactOccurred('light');
}

function handleTapConfirmed(taps) {
    tapCount += taps;
    updateTapCounter();
    showFloatingNumber(taps);
}

function updateTapCounter() {
    document.getElementById('my-taps-count').textContent = tapCount;
}

function showFloatingNumber(value) {
    const counter = document.getElementById('tap-counter');
    counter.textContent = `+${value}`;
    counter.style.animation = 'none';
    
    setTimeout(() => {
        counter.style.animation = 'floatUp 1s ease-out';
    }, 10);
}

// ========== АНИМАЦИИ ==========

function createParticles(e) {
    const rect = e.target.getBoundingClientRect();
    const x = e.touches ? e.touches[0].clientX : e.clientX;
    const y = e.touches ? e.touches[0].clientY : e.clientY;
    
    // Создаем 5-10 частиц
    const particleCount = Math.floor(Math.random() * 6) + 5;
    
    for (let i = 0; i < particleCount; i++) {
        particles.push({
            x: x,
            y: y,
            vx: (Math.random() - 0.5) * 8,
            vy: (Math.random() - 0.5) * 8 - 3,
            life: 1.0,
            size: Math.random() * 4 + 2,
            color: `hsl(${Math.random() * 60 + 30}, 100%, 60%)`
        });
    }
}

function animate() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Обновляем и рисуем частицы
    particles = particles.filter(particle => {
        particle.x += particle.vx;
        particle.y += particle.vy;
        particle.vy += 0.3; // Гравитация
        particle.life -= 0.02;
        
        if (particle.life > 0) {
            ctx.save();
            ctx.globalAlpha = particle.life;
            ctx.fillStyle = particle.color;
            ctx.beginPath();
            ctx.arc(particle.x, particle.y, particle.size, 0, Math.PI * 2);
            ctx.fill();
            ctx.restore();
            return true;
        }
        return false;
    });
    
    animationFrame = requestAnimationFrame(animate);
}

function animateButton() {
    const button = document.getElementById('tap-button');
    button.style.transform = 'scale(0.9)';
    
    setTimeout(() => {
        button.style.transform = 'scale(1)';
    }, 100);
}

// ========== БУСТЫ ==========

async function activateBoost(boostType) {
    // Проверяем баланс (упрощенно)
    const prices = {
        '2x': 10,
        '3x': 25,
        'turbo': 15
    };
    
    const price = prices[boostType];
    
    // Подтверждение покупки
    tg.showConfirm(
        `Активировать буст ${boostType.toUpperCase()} за ${price} ⭐?`,
        async (confirmed) => {
            if (confirmed) {
                // Отправляем на сервер
                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify({
                        type: 'boost',
                        boost_type: boostType
                    }));
                }
            }
        }
    );
}

function handleBoostActivated(data) {
    if (!data.success) {
        tg.showAlert('Не удалось активировать буст');
        return;
    }
    
    const multipliers = {
        '2x': 2.0,
        '3x': 3.0,
        'turbo': 5.0
    };
    
    const durations = {
        '2x': 30,
        '3x': 30,
        'turbo': 10
    };
    
    currentMultiplier = multipliers[data.boost_type];
    const duration = durations[data.boost_type];
    
    // Визуальный эффект
    showBoostEffect(data.boost_type, duration);
    
    // Автоматически сбрасываем множитель
    setTimeout(() => {
        currentMultiplier = 1.0;
        hideBoostEffect();
    }, duration * 1000);
    
    tg.HapticFeedback.notificationOccurred('success');
}

function showBoostEffect(boostType, duration) {
    const tapButton = document.getElementById('tap-button');
    
    // Меняем стиль кнопки
    if (boostType === '2x') {
        tapButton.style.background = 'linear-gradient(135deg, #a8e6cf 0%, #3ecd5e 100%)';
        tapButton.style.boxShadow = '0 20px 60px rgba(62, 205, 94, 0.8)';
    } else if (boostType === '3x') {
        tapButton.style.background = 'linear-gradient(135deg, #ffa502 0%, #ff6348 100%)';
        tapButton.style.boxShadow = '0 20px 60px rgba(255, 99, 72, 0.8)';
    } else if (boostType === 'turbo') {
        tapButton.style.background = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
        tapButton.style.boxShadow = '0 20px 60px rgba(118, 75, 162, 0.8)';
        tapButton.style.animation = 'pulse 0.3s infinite';
    }
    
    // Добавляем текст множителя
    tapButton.innerHTML = `👆 TAP!<br><span style="font-size: 20px;">x${currentMultiplier}</span>`;
}

function hideBoostEffect() {
    const tapButton = document.getElementById('tap-button');
    tapButton.style.background = 'linear-gradient(135deg, #ffeaa7 0%, #fdcb6e 100%)';
    tapButton.style.boxShadow = '0 20px 60px rgba(253, 203, 110, 0.6)';
    tapButton.style.animation = 'none';
    tapButton.innerHTML = '👆 TAP!';
}

// ========== МИНИ ЛИДЕРБОРД ==========

function updateMiniLeaderboard(leaderboard) {
    const container = document.getElementById('live-leaderboard');
    
    let html = '';
    leaderboard.slice(0, 5).forEach((player, index) => {
        const [userId, username, taps] = player;
        const isMe = userId === currentUser.user_id;
        const medal = ['🥇', '🥈', '🥉'][index] || `${index + 1}.`;
        
        html += `
            <div class="leaderboard-row ${isMe ? 'highlight' : ''}">
                <span>${medal}</span>
                <span>${username || 'Player'}</span>
                <span>${taps}</span>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

// ========== ОКОНЧАНИЕ ИГРЫ ==========

function endGame() {
    // Останавливаем анимацию
    if (animationFrame) {
        cancelAnimationFrame(animationFrame);
    }
    
    // Убираем обработчики
    const tapButton = document.getElementById('tap-button');
    tapButton.removeEventListener('touchstart', handleTap);
    tapButton.removeEventListener('click', handleTap);
    
    tg.showPopup({
        title: '⏱ Время вышло!',
        message: 'Подсчитываем результаты...',
        buttons: []
    });
}

// ========== РЕЗУЛЬТАТЫ ==========

function showResults(results) {
    tg.closePopup();
    showScreen('results-screen');
    
    // Находим свой результат
    const myResult = results.find(r => r.user_id === currentUser.user_id);
    
    if (!myResult) {
        tg.showAlert('Ошибка получения результатов');
        return;
    }
    
    // Обновляем UI
    document.getElementById('my-position').textContent = `#${myResult.position}`;
    document.getElementById('my-final-taps').textContent = myResult.taps;
    
    const prizeElement = document.getElementById('my-prize');
    if (myResult.prize > 0) {
        prizeElement.textContent = `${myResult.prize} ⭐`;
        prizeElement.style.color = '#ffd93d';
        document.getElementById('result-title').textContent = '🎉 ТЫ ВЫИГРАЛ!';
        
        // Конфетти анимация
        celebrateWin();
        
        tg.HapticFeedback.notificationOccurred('success');
    } else {
        prizeElement.textContent = '0 ⭐';
        prizeElement.style.color = '#95a5a6';
        document.getElementById('result-title').textContent = '😔 В следующий раз повезет!';
    }
    
    // Показываем топ-5
    const winnersList = document.getElementById('winners-list');
    let html = '<h3>🏆 Топ-5 победителей</h3>';
    
    results.slice(0, 5).forEach((result, index) => {
        const medals = ['🥇', '🥈', '🥉', '4️⃣', '5️⃣'];
        html += `
            <div class="winner-item">
                <span class="winner-medal">${medals[index]}</span>
                <span class="winner-name">${result.username || 'Player'}</span>
                <span class="winner-taps">${result.taps} тапов</span>
                <span class="winner-prize">${result.prize} ⭐</span>
            </div>
        `;
    });
    
    winnersList.innerHTML = html;
    
    // Обновляем данные пользователя
    updateUserData();
}

function celebrateWin() {
    // Создаем конфетти
    for (let i = 0; i < 100; i++) {
        setTimeout(() => {
            const x = Math.random() * window.innerWidth;
            particles.push({
                x: x,
                y: -10,
                vx: (Math.random() - 0.5) * 3,
                vy: Math.random() * 3 + 2,
                life: 1.0,
                size: Math.random() * 6 + 3,
                color: `hsl(${Math.random() * 360}, 100%, 60%)`
            });
        }, i * 20);
    }
    
    // Продолжаем анимацию
    if (!animationFrame) {
        animate();
    }
}

async function updateUserData() {
    try {
        const response = await fetch(`${API_URL}/api/user/${currentUser.user_id}`);
        const userData = await response.json();
        currentUser = userData;
        updateUserInfo();
    } catch (error) {
        console.error('Update user data error:', error);
    }
}

// ========== CSS ДОПОЛНЕНИЯ ==========

const additionalStyles = `
@keyframes pulse {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.05); }
}

.leaderboard-row {
    display: flex;
    justify-content: space-between;
    padding: 8px;
    margin: 5px 0;
    background: rgba(255,255,255,0.1);
    border-radius: 8px;
}

.leaderboard-row.highlight {
    background: rgba(255, 215, 0, 0.3);
    border: 2px solid gold;
}

.winner-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 15px;
    margin: 10px 0;
    background: rgba(255,255,255,0.1);
    border-radius: 12px;
}

.winner-medal {
    font-size: 24px;
}

.winner-name {
    flex: 1;
    font-weight: bold;
}

.winner-prize {
    color: #ffd93d;
    font-weight: bold;
}

.info-card {
    background: rgba(255,255,255,0.15);
    padding: 20px;
    border-radius: 15px;
    text-align: center;
    margin: 10px 0;
}

.info-card span {
    display: block;
    font-size: 14px;
    opacity: 0.8;
    margin-bottom: 8px;
}

.info-card strong {
    font-size: 24px;
    color: #ffd93d;
}

.prize-list {
    background: rgba(0,0,0,0.2);
    padding: 15px;
    border-radius: 12px;
    margin: 15px 0;
}

.prize-item {
    padding: 10px;
    margin: 5px 0;
    background: rgba(255,255,255,0.1);
    border-radius: 8px;
}
`;

// Добавляем стили
const styleSheet = document.createElement('style');
styleSheet.textContent = additionalStyles;
document.head.appendChild(styleSheet);