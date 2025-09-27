from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from flask import Flask, request, jsonify
from flask_cors import CORS
import threading
import random
import json
import requests
import time

# Flask App for Frontend-Backend Communication
app_flask = Flask(__name__)
CORS(app_flask)

# Telegram Bot Configuration - YAHAN APNA DATA DALNA
API_ID = "23739381"
API_HASH = "77784995504d21faf90ebb0a4bcfc37a"
BOT_TOKEN = "8211158600:AAG8c1qJrRXKg-RGyZBgjOpXmwH4P3i4TEk"

# Initialize Telegram Bot
app_telegram = Client("snake_ladder_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Game Data Storage
active_games = {}

class SnakeLadderGame:
    def __init__(self, game_code, host_id):
        self.game_code = game_code
        self.host_id = host_id
        self.players = {}
        self.status = "waiting"
        self.current_turn = 0
        self.moves_history = []
        
        self.snakes = {16: 6, 47: 26, 49: 11, 56: 53, 62: 19, 64: 60, 87: 24, 93: 73, 95: 75, 98: 78}
        self.ladders = {1: 38, 4: 14, 9: 31, 21: 42, 28: 84, 36: 44, 51: 67, 71: 91, 80: 100}
    
    def add_player(self, user_id, username):
        if len(self.players) >= 4:
            return False
        
        color_options = ['#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4']
        self.players[user_id] = {
            'username': username,
            'position': 1,
            'color': color_options[len(self.players)],
            'ready': True
        }
        return True
    
    def start_game(self):
        if len(self.players) < 1:
            return False
        self.status = "playing"
        self.current_turn = list(self.players.keys())[0]
        return True
    
    def make_move(self, user_id, dice_value):
        if user_id != self.current_turn:
            return {"error": "Not your turn"}
        
        player = self.players[user_id]
        new_position = player['position'] + dice_value
        
        if new_position > 100:
            return {"error": "Need exact roll to win"}
        
        move_info = {
            'player': user_id,
            'dice_value': dice_value,
            'from_position': player['position'],
            'to_position': new_position,
            'special_move': None
        }
        
        if new_position in self.snakes:
            move_info['special_move'] = f"snake_{new_position}_{self.snakes[new_position]}"
            new_position = self.snakes[new_position]
        elif new_position in self.ladders:
            move_info['special_move'] = f"ladder_{new_position}_{self.ladders[new_position]}"
            new_position = self.ladders[new_position]
        
        player['position'] = new_position
        self.moves_history.append(move_info)
        
        if new_position == 100:
            self.status = "finished"
            return {"winner": user_id, "new_position": new_position}
        
        player_ids = list(self.players.keys())
        current_index = player_ids.index(user_id)
        next_index = (current_index + 1) % len(player_ids)
        self.current_turn = player_ids[next_index]
        
        return {"success": True, "new_position": new_position, "next_player": self.current_turn}

# Flask API Routes
@app_flask.route('/')
def serve_game():
    return """
    <html>
    <head>
        <title>Snake Ladder Game</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { 
                font-family: Arial, sans-serif; 
                text-align: center; 
                padding: 50px; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                min-height: 100vh;
                margin: 0;
            }
            .container {
                background: rgba(255,255,255,0.1);
                padding: 30px;
                border-radius: 15px;
                backdrop-filter: blur(10px);
                max-width: 500px;
                margin: 0 auto;
            }
            .btn { 
                padding: 15px 30px; 
                font-size: 18px; 
                margin: 10px; 
                cursor: pointer;
                background: #4CAF50;
                color: white;
                border: none;
                border-radius: 8px;
                text-decoration: none;
                display: inline-block;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🐍 Snake Ladder Game</h1>
            <p>🚀 This game is running locally on your PC</p>
            <p>💡 Use your Telegram bot to play the game</p>
            <p>🤖 Send <code>/start</code> to your bot</p>
            <br>
            <button class="btn" onclick="window.close()">Close</button>
        </div>
    </body>
    </html>
    """

@app_flask.route('/game.html')
def serve_game_html():
    # Get parameters from URL
    game_code = request.args.get('game_code', '')
    user_id = request.args.get('user_id', '')
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Snake Ladder Game</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <script src="https://telegram.org/js/telegram-web-app.js"></script>
        <style>
            body {{ 
                font-family: Arial, sans-serif; 
                text-align: center; 
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                min-height: 100vh;
                margin: 0;
            }}
            .game-container {{
                background: rgba(255,255,255,0.1);
                padding: 20px;
                border-radius: 15px;
                backdrop-filter: blur(10px);
                max-width: 400px;
                margin: 0 auto;
            }}
            .btn {{ 
                padding: 12px 24px; 
                font-size: 16px; 
                margin: 10px; 
                cursor: pointer;
                background: #4CAF50;
                color: white;
                border: none;
                border-radius: 8px;
            }}
        </style>
    </head>
    <body>
        <div class="game-container">
            <h1>🐍 Snake Ladder</h1>
            <p>Game Code: <strong>{game_code}</strong></p>
            <p>User ID: <strong>{user_id}</strong></p>
            <br>
            <p>🎮 Game would load here in full version</p>
            <p>📱 This is a placeholder for Telegram Web App</p>
            <br>
            <button class="btn" onclick="playGame()">Play Demo</button>
            <button class="btn" onclick="window.Telegram.WebApp.close()">Close</button>
        </div>
        
        <script>
            function playGame() {{
                alert('🎲 Full game would load here!\\n\\nIn complete version, this would be the actual Snake Ladder game.');
            }}
            
            // Initialize Telegram Web App
            if (window.Telegram && window.Telegram.WebApp) {{
                Telegram.WebApp.expand();
                Telegram.WebApp.ready();
            }}
        </script>
    </body>
    </html>
    """

@app_flask.route('/api/game_state', methods=['POST'])
def api_game_state():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data received'})
            
        game_code = data.get('game_code')
        
        if game_code in active_games:
            game = active_games[game_code]
            return jsonify({
                'players': game.players,
                'current_turn': game.current_turn,
                'status': game.status,
                'moves_history': game.moves_history[-10:]
            })
        else:
            return jsonify({'error': 'Game not found'})
    except Exception as e:
        return jsonify({'error': str(e)})

@app_flask.route('/api/make_move', methods=['POST'])
def api_make_move():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data received'})
            
        game_code = data.get('game_code')
        user_id = data.get('user_id')
        dice_value = data.get('dice_value')
        
        if game_code in active_games:
            game = active_games[game_code]
            result = game.make_move(int(user_id), dice_value)
            return jsonify(result)
        else:
            return jsonify({'error': 'Game not found'})
    except Exception as e:
        return jsonify({'error': str(e)})

@app_flask.route('/api/create_game', methods=['POST'])
def api_create_game():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data received'})
            
        user_id = data.get('user_id')
        username = data.get('username')
        
        game_code = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=6))
        game = SnakeLadderGame(game_code, user_id)
        game.add_player(int(user_id), username)
        active_games[game_code] = game
        
        return jsonify({'game_code': game_code, 'status': 'created'})
    except Exception as e:
        return jsonify({'error': str(e)})

# Telegram Bot Handlers
@app_telegram.on_message(filters.command("start"))
async def start_command(client, message):
    # Local IP for WebApp URL
    local_ip = get_local_ip()
    web_app_url = f"https://cot-8kof.onrender.com/game.html?user_id={message.from_user.id}"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 Play Game", web_app=WebAppInfo(url=web_app_url))],
        [InlineKeyboardButton("👥 Create Multiplayer Game", callback_data="create_multiplayer")],
        [InlineKeyboardButton("📖 How to Play", callback_data="show_help")]
    ])
    
    await message.reply_text(
        "🐍 **Snake Ladder Bot** 🎲\n\n"
        "Welcome to the classic Snake Ladder game!\n\n"
        "**Features:**\n"
        "• 🎮 Single Player & Multiplayer\n"
        "• 👥 Play with friends\n"
        "• 🎲 Smooth gameplay\n"
        "• 📱 Mobile optimized\n\n"
        "Click below to start playing:",
        reply_markup=keyboard
    )

@app_telegram.on_message(filters.command("play"))
async def play_command(client, message):
    game_code = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=6))
    game = SnakeLadderGame(game_code, message.from_user.id)
    game.add_player(message.from_user.id, message.from_user.first_name)
    active_games[game_code] = game
    
    local_ip = get_local_ip()
    game_url = f"http://{local_ip}:5000/game.html?game_code={game_code}&user_id={message.from_user.id}"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 Join Game", web_app=WebAppInfo(url=game_url))],
        [InlineKeyboardButton("📤 Share Game Code", url=f"https://t.me/share/url?url=Join my game! Use code: {game_code}")]
    ])
    
    await message.reply_text(
        f"🎮 **Multiplayer Game Created!**\n\n"
        f"**Game Code:** `{game_code}`\n"
        f"**Players:** 1/4\n\n"
        f"**How to join:**\n"
        f"1. Share this code with friends\n"
        f"2. Friends use: `/join {game_code}`\n"
        f"3. Or click below to play now",
        reply_markup=keyboard
    )

@app_telegram.on_message(filters.command("join"))
async def join_command(client, message):
    if len(message.command) < 2:
        await message.reply_text("❌ Usage: `/join GAMECODE`")
        return
    
    game_code = message.command[1].upper()
    
    if game_code not in active_games:
        await message.reply_text("❌ Game not found! Check the game code.")
        return
    
    game = active_games[game_code]
    
    if game.status != "waiting":
        await message.reply_text("❌ Game has already started!")
        return
    
    success = game.add_player(message.from_user.id, message.from_user.first_name)
    
    if success:
        local_ip = get_local_ip()
        game_url = f"https://cot-8kof.onrender.com/game.html?game_code={game_code}&user_id={message.from_user.id}"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎮 Play Now", web_app=WebAppInfo(url=game_url))]
        ])
        
        await message.reply_text(
            f"✅ **Joined Game Successfully!**\n\n"
            f"**Game Code:** `{game_code}`\n"
            f"**Players:** {len(game.players)}/4\n\n"
            f"Click below to start playing:",
            reply_markup=keyboard
        )
        
        # Notify host
        await client.send_message(
            game.host_id,
            f"👤 **{message.from_user.first_name} joined your game!**\n"
            f"Game Code: {game_code}\n"
            f"Total players: {len(game.players)}/4"
        )
    else:
        await message.reply_text("❌ Game is full! Maximum 4 players allowed.")

@app_telegram.on_callback_query()
async def handle_callbacks(client, callback_query):
    data = callback_query.data
    user_id = callback_query.from_user.id
    
    if data == "create_multiplayer":
        await play_command(client, callback_query.message)
    
    elif data == "show_help":
        await callback_query.message.edit_text(
            "📖 **How to Play Snake Ladder**\n\n"
            "**Game Rules:**\n"
            "• 🎲 Roll dice to move forward\n"
            "• 🐍 Land on snake head → Go to tail\n"
            "• 🪜 Land on ladder bottom → Climb to top\n"
            "• 🏁 First to reach exactly 100 wins!\n\n"
            "**Multiplayer:**\n"
            "• Use `/play` to create a game\n"
            "• Share the game code with friends\n"
            "• Friends use `/join CODE` to join\n"
            "• Up to 4 players can play together\n",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎮 Start Playing", callback_data="start_playing")],
                [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
            ])
        )
    
    elif data == "start_playing":
        await start_command(client, callback_query.message)
    
    elif data == "back_to_start":
        await start_command(client, callback_query.message)

def get_local_ip():
    """Get local IP address for network access"""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def run_flask():
    """Run Flask server in separate thread"""
    print("🌐 Starting Web Server on port 5000...")
    app_flask.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

def run_telegram():
    """Run Telegram bot"""
    print("🤖 Starting Telegram Bot...")
    app_telegram.run()

def get_bot_username():
    """Safely get bot username"""
    try:
        with app_telegram:
            me = app_telegram.get_me()
            return me.username
    except:
        return "your_bot_username"

if __name__ == "__main__":
    print("🚀 Starting Snake Ladder Telegram Game System...")
    print("=" * 50)
    
    local_ip = get_local_ip()
    bot_username = get_bot_username()
    
    print(f"🌐 Local Access: http://localhost:5000")
    print(f"🌐 Network Access: http://{local_ip}:5000")
    print(f"🤖 Bot Username: @{bot_username}")
    print("=" * 50)
    print("💡 Instructions:")
    print("1. Open Telegram and search for your bot")
    print("2. Send /start command to the bot")
    print("3. Click 'Play Game' to start playing")
    print("=" * 50)
    
    # Start Flask server in background thread
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # Wait for Flask to start
    time.sleep(3)
    
    # Start Telegram bot
    try:
        print("🤖 Bot is starting...")
        app_telegram.run()
    except Exception as e:
        print(f"❌ Error: {e}")

        print("💡 Check your API_ID, API_HASH and BOT_TOKEN")
