<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Snake Ladder - 2 Player Game</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh; padding: 20px; color: white;
        }
        .container { max-width: 400px; margin: 0 auto; }
        .glass-effect {
            background: rgba(255, 255, 255, 0.1); backdrop-filter: blur(10px);
            border-radius: 20px; border: 1px solid rgba(255, 255, 255, 0.2);
            padding: 20px; box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }
        h1 { text-align: center; font-size: 2.2em; margin-bottom: 10px; }
        .mode-buttons { display: grid; gap: 15px; margin: 20px 0; }
        .btn {
            padding: 15px; border: none; border-radius: 15px; font-size: 1.1em;
            font-weight: 600; cursor: pointer; transition: all 0.3s ease;
        }
        .btn-primary { background: linear-gradient(135deg, #ff6b6b, #ee5a24); color: white; }
        .btn-secondary { background: linear-gradient(135deg, #4ecdc4, #44a08d); color: white; }
        .board {
            display: grid; grid-template-columns: repeat(10, 1fr); 
            width: 100%; aspect-ratio: 1/1; border: 3px solid #2d3748; 
            border-radius: 10px; background: white; margin: 15px 0;
        }
        .cell { border: 1px solid #cbd5e0; position: relative; background: #f7fafc; }
        .cell-number { position: absolute; top: 2px; left: 2px; font-size: 8px; color: #718096; }
        .player { width: 12px; height: 12px; border-radius: 50%; border: 2px solid white; position: absolute; }
        .dice { 
            width: 60px; height: 60px; background: linear-gradient(135deg, #ffd89b, #19547b); 
            border: none; border-radius: 12px; font-size: 24px; cursor: pointer; margin: 10px auto;
            display: block;
        }
        .game-info { background: rgba(255,255,255,0.1); padding: 10px; border-radius: 10px; margin: 10px 0; }
        .notification {
            position: fixed; top: 10px; right: 10px; background: #4CAF50; color: white; 
            padding: 12px; border-radius: 8px; z-index: 1000; display: none;
        }
        .waiting { 
            background: rgba(255,255,255,0.15); padding: 15px; border-radius: 10px; 
            text-align: center; margin: 10px 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Main Menu -->
        <div id="mainMenu" class="glass-effect">
            <h1>🐍 Snakes & Ladders</h1>
            <p style="text-align: center; opacity: 0.9;">2 Player Game</p>
            
            <div class="mode-buttons">
                <button class="btn btn-primary" onclick="createGame()">🎮 Create Game</button>
                <button class="btn btn-secondary" onclick="showJoinScreen()">👥 Join Game</button>
            </div>

            <div id="joinSection" style="display: none;">
                <input type="text" id="gameCodeInput" placeholder="Enter Game Code" 
                       style="width: 100%; padding: 12px; border-radius: 10px; border: none; margin: 10px 0;">
                <button class="btn btn-secondary" onclick="joinGame()" style="width: 100%;">Join Game</button>
            </div>
        </div>

        <!-- Game Screen -->
        <div id="gameScreen" class="glass-effect" style="display: none;">
            <div id="waitingMessage" class="waiting">
                <h3>⏳ Waiting for Player 2...</h3>
                <p>Game Code: <strong id="gameCodeDisplay"></strong></p>
                <p>Share this code with a friend!</p>
            </div>

            <div class="game-info" id="gameStatus">🎯 Your Turn - Roll the Dice!</div>
            <div class="game-info" id="playersInfo"></div>
            
            <div class="board" id="gameBoard"></div>

            <button class="dice" id="diceBtn" onclick="rollDice()">🎲</button>
            
            <button class="btn" onclick="showMainMenu()" 
                    style="background: rgba(255,255,255,0.2); color: white; width: 100%; margin-top: 10px;">
                🏠 Main Menu
            </button>
        </div>
    </div>

    <div class="notification" id="notification"></div>

    <script>
        // Game Configuration
        const snakes = {16:6,47:26,49:11,56:53,62:19,64:60,87:24,93:73,95:75,98:78};
        const ladders = {1:38,4:14,9:31,21:42,28:84,36:44,51:67,71:91,80:100};
        const playerColors = ['#ff6b6b', '#4ecdc4']; // Only 2 colors
        
        // Game State
        let gameState = {
            players: [],
            currentPlayer: null,
            gameActive: false,
            gameCode: null,
            userData: null,
            backendUrl: 'https://cot-8kof.onrender.com/api' // YOUR RENDER.COM URL
        };

        // Telegram Web App
        let tg = window.Telegram?.WebApp;

        // Initialize
        function initGame() {
            if (tg) {
                tg.expand();
                tg.enableClosingConfirmation();
                gameState.userData = tg.initDataUnsafe?.user;
            }

            // Check if joining via URL parameter
            const urlParams = new URLSearchParams(window.location.search);
            const gameCode = urlParams.get('game_code');
            
            if (gameCode) {
                joinGameWithCode(gameCode);
            }
        }

        // Show/Hide Screens
        function showMainMenu() {
            document.getElementById('mainMenu').style.display = 'block';
            document.getElementById('gameScreen').style.display = 'none';
            document.getElementById('joinSection').style.display = 'none';
        }

        function showJoinScreen() {
            document.getElementById('joinSection').style.display = 'block';
        }

        // Create Game
        async function createGame() {
            const user = gameState.userData || {id: Date.now(), first_name: 'Player'};
            
            try {
                const response = await fetch(gameState.backendUrl + '/create_game', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        user_id: user.id,
                        username: user.first_name || 'Player'
                    })
                });
                
                const result = await response.json();
                
                if (result.game_code) {
                    gameState.gameCode = result.game_code;
                    showGameScreen();
                    startGamePolling();
                    showNotification('Game created! Share the code with a friend.');
                } else {
                    showNotification('Failed to create game');
                }
            } catch (error) {
                showNotification('Error connecting to server');
            }
        }

        // Join Game
        async function joinGame() {
            const gameCode = document.getElementById('gameCodeInput').value.toUpperCase();
            if (!gameCode) {
                showNotification('Please enter game code');
                return;
            }
            joinGameWithCode(gameCode);
        }

        async function joinGameWithCode(gameCode) {
            const user = gameState.userData || {id: Date.now(), first_name: 'Player'};
            
            try {
                const response = await fetch(gameState.backendUrl + '/join_game', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        game_code: gameCode,
                        user_id: user.id,
                        username: user.first_name || 'Player'
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    gameState.gameCode = gameCode;
                    showGameScreen();
                    startGamePolling();
                    showNotification('Joined game successfully!');
                } else {
                    showNotification(result.error || 'Failed to join game');
                }
            } catch (error) {
                showNotification('Error connecting to server');
            }
        }

        // Game Screen
        function showGameScreen() {
            document.getElementById('mainMenu').style.display = 'none';
            document.getElementById('gameScreen').style.display = 'block';
            createBoard();
        }

        // Game Polling
        let pollInterval;
        function startGamePolling() {
            pollInterval = setInterval(updateGameState, 2000);
            updateGameState(); // Immediate first update
        }

        async function updateGameState() {
            if (!gameState.gameCode) return;
            
            try {
                const response = await fetch(gameState.backendUrl + '/game_state', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({game_code: gameState.gameCode})
                });
                
                const gameData = await response.json();
                
                if (gameData.error) {
                    showNotification(gameData.error);
                    return;
                }
                
                updateGameUI(gameData);
                
            } catch (error) {
                console.error('Error updating game:', error);
            }
        }

        function updateGameUI(gameData) {
            // Update players
            gameState.players = Object.values(gameData.players || {});
            gameState.currentPlayer = gameData.current_turn;
            gameState.gameActive = gameData.status === 'playing';
            
            // Show/hide waiting message
            const waitingDiv = document.getElementById('waitingMessage');
            if (gameData.status === 'waiting') {
                waitingDiv.style.display = 'block';
                document.getElementById('gameCodeDisplay').textContent = gameState.gameCode;
                document.getElementById('diceBtn').style.display = 'none';
            } else {
                waitingDiv.style.display = 'none';
                document.getElementById('diceBtn').style.display = 'block';
            }
            
            // Update UI
            updatePlayersInfo();
            updateGameStatus();
            placePlayers();
        }

        // Game Functions
        function createBoard() {
            const board = document.getElementById('gameBoard');
            board.innerHTML = '';
            
            for (let row = 10; row >= 1; row--) {
                for (let col = 1; col <= 10; col++) {
                    const position = row % 2 === 0 ? (row-1)*10 + col : (row-1)*10 + (11-col);
                    const cell = document.createElement('div');
                    cell.className = 'cell';
                    cell.innerHTML = `<div class="cell-number">${position}</div>`;
                    
                    if (snakes[position]) {
                        cell.innerHTML += `<div style="position:absolute;bottom:1px;right:1px;font-size:10px;">🐍</div>`;
                    }
                    if (ladders[position]) {
                        cell.innerHTML += `<div style="position:absolute;top:1px;left:1px;font-size:10px;">🪜</div>`;
                    }
                    
                    board.appendChild(cell);
                }
            }
        }

        function updatePlayersInfo() {
            const container = document.getElementById('playersInfo');
            container.innerHTML = '';
            
            gameState.players.forEach((player, index) => {
                const isCurrent = player.id == gameState.currentPlayer;
                container.innerHTML += `
                    <div style="display: flex; justify-content: space-between; padding: 5px; 
                         background: ${isCurrent ? 'rgba(255,255,255,0.2)' : 'transparent'}; 
                         border-radius: 5px; margin: 2px 0;">
                        <span>${player.username}</span>
                        <span>Position: ${player.position}</span>
                    </div>
                `;
            });
        }

        function updateGameStatus() {
            const status = document.getElementById('gameStatus');
            
            // Check for winner
            const winner = gameState.players.find(p => p.position === 100);
            if (winner) {
                status.innerHTML = `🎉 ${winner.username} Wins! 🏆`;
                gameState.gameActive = false;
                return;
            }
            
            if (!gameState.gameActive) {
                status.innerHTML = '⏳ Waiting for players...';
                return;
            }
            
            const currentPlayer = gameState.players.find(p => p.id == gameState.currentPlayer);
            const user = gameState.userData;
            const isMyTurn = currentPlayer && user && currentPlayer.id == user.id;
            
            status.innerHTML = `🎯 ${currentPlayer?.username || 'Player'}'s Turn - ${isMyTurn ? 'Roll the Dice!' : 'Waiting...'}`;
        }

        function placePlayers() {
            document.querySelectorAll('.player').forEach(p => p.remove());
            
            gameState.players.forEach((player, index) => {
                const cells = document.querySelectorAll('.cell');
                if (player.position <= 100 && cells[player.position - 1]) {
                    const token = document.createElement('div');
                    token.className = 'player';
                    token.style.background = playerColors[index] || '#ccc';
                    token.style.left = (index * 15 + 5) + 'px';
                    token.style.top = '5px';
                    cells[player.position - 1].appendChild(token);
                }
            });
        }

        // Dice Roll
        async function rollDice() {
            if (!gameState.gameActive) return;
            
            const user = gameState.userData;
            if (!user) return;
            
            const currentPlayer = gameState.players.find(p => p.id == gameState.currentPlayer);
            if (!currentPlayer || currentPlayer.id != user.id) {
                showNotification("Wait for your turn!");
                return;
            }
            
            const diceBtn = document.getElementById('diceBtn');
            diceBtn.disabled = true;
            
            const diceValue = Math.floor(Math.random() * 6) + 1;
            
            try {
                const response = await fetch(gameState.backendUrl + '/make_move', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        game_code: gameState.gameCode,
                        user_id: user.id,
                        dice_value: diceValue
                    })
                });
                
                const result = await response.json();
                
                if (result.error) {
                    showNotification(result.error);
                }
                
            } catch (error) {
                showNotification('Error making move');
            }
            
            diceBtn.disabled = false;
        }

        // Utilities
        function showNotification(message) {
            const notification = document.getElementById('notification');
            notification.textContent = message;
            notification.style.display = 'block';
            setTimeout(() => notification.style.display = 'none', 3000);
        }

        // Initialize when page loads
        window.addEventListener('DOMContentLoaded', initGame);
    </script>
</body>
</html>

