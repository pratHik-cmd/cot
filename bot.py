from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from flask import Flask, request, jsonify
from flask_cors import CORS
import threading
import random
import json
import sqlite3
from datetime import datetime, timedelta
import time
import os

# Flask App for Backend API
app_flask = Flask(__name__)
CORS(app_flask)

# Telegram Bot Configuration - TERA EXISTING DATA
API_ID = "23739381"
API_HASH = "77784995504d21faf90ebb0a4bcfc37a"
BOT_TOKEN = "8211158600:AAG8c1qJrRXKg-RGyZBgjOpXmwH4P3i4TEk"

# Initialize Telegram Bot
app_telegram = Client("snake_ladder_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Frontend URL (GitHub Pages) - TERA EXISTING BACKEND URL
FRONTEND_URL = "https://pratHik-cmd.github.io/snake-ladder-game"  # YEH CHANGE KARNA HAI
BACKEND_URL = "https://cot-8kof.onrender.com/api"

# Database Setup
def init_db():
    conn = sqlite3.connect('games.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS games
                 (game_code TEXT PRIMARY KEY, players TEXT, status TEXT, 
                  current_turn INTEGER, created_at TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

# Game Management
class GameManager:
    def __init__(self):
        self.games = {}
        self.snakes = {16:6,47:26,49:11,56:53,62:19,64:60,87:24,93:73,95:75,98:78}
        self.ladders = {1:38,4:14,9:31,21:42,28:84,36:44,51:67,71:91,80:100}
    
    def create_game(self, user_id, username, game_type="multiplayer"):
        game_code = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=6))
        
        players = {
            str(user_id): {
                'name': username,
                'position': 1,
                'color': '#ff6b6b',
                'type': 'human'
            }
        }
        
        game_data = {
            'players': players,
            'status': 'waiting' if game_type == "multiplayer" else 'playing',
            'current_turn': user_id,
            'game_type': game_type,
            'created_at': datetime.now(),
            'min_players': 2 if game_type == "multiplayer" else 1
        }
        
        # Save to database
        conn = sqlite3.connect('games.db')
        c = conn.cursor()
        c.execute('INSERT INTO games VALUES (?, ?, ?, ?, ?)',
                  (game_code, json.dumps(players), game_data['status'], user_id, datetime.now()))
        conn.commit()
        conn.close()
        
        self.games[game_code] = game_data
        return game_code
    
    def join_game(self, game_code, user_id, username):
        if game_code not in self.games:
            # Try to load from database
            conn = sqlite3.connect('games.db')
            c = conn.cursor()
            c.execute('SELECT * FROM games WHERE game_code = ?', (game_code,))
            result = c.fetchone()
            conn.close()
            
            if not result:
                return False, "Game not found"
            
            game_data = {
                'players': json.loads(result[1]),
                'status': result[2],
                'current_turn': result[3],
                'created_at': result[4],
                'game_type': 'multiplayer',
                'min_players': 2
            }
            self.games[game_code] = game_data
        
        game = self.games[game_code]
        
        if game['game_type'] != 'multiplayer':
            return False, "This is a single player game"
        
        if len(game['players']) >= 4:
            return False, "Game is full"
        
        if str(user_id) in game['players']:
            return False, "Already in game"
        
        colors = ['#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4']
        game['players'][str(user_id)] = {
            'name': username,
            'position': 1,
            'color': colors[len(game['players'])],
            'type': 'human'
        }
        
        # Start game if enough players
        if len(game['players']) >= game['min_players']:
            game['status'] = 'playing'
        
        # Update database
        conn = sqlite3.connect('games.db')
        c = conn.cursor()
        c.execute('UPDATE games SET players = ?, status = ? WHERE game_code = ?',
                  (json.dumps(game['players']), game['status'], game_code))
        conn.commit()
        conn.close()
        
        return True, "Joined successfully"
    
    def make_move(self, game_code, user_id, dice_value):
        if game_code not in self.games:
            return {'error': 'Game not found'}
        
        game = self.games[game_code]
        
        if game['status'] != 'playing':
            return {'error': 'Game not active'}
        
        if game['current_turn'] != user_id:
            return {'error': 'Not your turn'}
        
        player = game['players'][str(user_id)]
        new_position = player['position'] + dice_value
        
        if new_position > 100:
            return {'error': 'Need exact roll'}
        
        # Check for snakes and ladders
        if new_position in self.snakes:
            new_position = self.snakes[new_position]
        elif new_position in self.ladders:
            new_position = self.ladders[new_position]
        
        player['position'] = new_position
        
        # Check for winner
        if new_position == 100:
            game['status'] = 'finished'
            return {'winner': user_id, 'new_position': new_position}
        
        # Next player's turn
        player_ids = list(game['players'].keys())
        current_index = player_ids.index(str(user_id))
        next_index = (current_index + 1) % len(player_ids)
        game['current_turn'] = int(player_ids[next_index])
        
        # Update database
        conn = sqlite3.connect('games.db')
        c = conn.cursor()
        c.execute('UPDATE games SET players = ?, current_turn = ?, status = ? WHERE game_code = ?',
                  (json.dumps(game['players']), game['current_turn'], game['status'], game_code))
        conn.commit()
        conn.close()
        
        return {'success': True, 'new_position': new_position}

game_manager = GameManager()

# Flask API Routes
@app_flask.route('/')
def home():
    return jsonify({
        "status": "Snake Ladder Backend API",
        "message": "Backend is running on Render.com!",
        "frontend_url": FRONTEND_URL,
        "backend_url": BACKEND_URL
    })

@app_flask.route('/api/health')
def health_check():
    return jsonify({"status": "healthy", "games_count": len(game_manager.games)})

@app_flask.route('/api/create_game', methods=['POST'])
def api_create_game():
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        username = data.get('username')
        game_type = data.get('game_type', 'multiplayer')
        
        game_code = game_manager.create_game(user_id, username, game_type)
        return jsonify({
            'game_code': game_code, 
            'status': 'created',
            'game_type': game_type
        })
    except Exception as e:
        return jsonify({'error': str(e)})

@app_flask.route('/api/join_game', methods=['POST'])
def api_join_game():
    try:
        data = request.get_json()
        game_code = data.get('game_code')
        user_id = data.get('user_id')
        username = data.get('username')
        
        success, message = game_manager.join_game(game_code, user_id, username)
        return jsonify({
            'success': success, 
            'error': None if success else message
        })
    except Exception as e:
        return jsonify({'error': str(e)})

@app_flask.route('/api/game_state', methods=['POST'])
def api_game_state():
    try:
        data = request.get_json()
        game_code = data.get('game_code')
        
        if game_code in game_manager.games:
            game = game_manager.games[game_code]
            return jsonify({
                'players': game['players'],
                'current_turn': game['current_turn'],
                'status': game['status'],
                'game_type': game['game_type'],
                'min_players': game['min_players'],
                'can_start': len(game['players']) >= game['min_players']
            })
        else:
            return jsonify({'error': 'Game not found'})
    except Exception as e:
        return jsonify({'error': str(e)})

@app_flask.route('/api/make_move', methods=['POST'])
def api_make_move():
    try:
        data = request.get_json()
        game_code = data.get('game_code')
        user_id = data.get('user_id')
        dice_value = data.get('dice_value')
        
        result = game_manager.make_move(game_code, user_id, dice_value)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)})

# Telegram Bot Handlers
@app_telegram.on_message(filters.command("start"))
async def start_command(client, message):
    web_app_url = f"{FRONTEND_URL}?user_id={message.from_user.id}"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 Play Game", web_app=WebAppInfo(url=web_app_url))],
        [InlineKeyboardButton("👥 Create Multiplayer", callback_data="create_multiplayer")],
        [InlineKeyboardButton("📖 How to Play", callback_data="show_help")]
    ])
    
    await message.reply_text(
        "🐍 **Snake Ladder Bot** 🎲\n\n"
        "Welcome to the classic Snake Ladder game!\n\n"
        "**Multiplayer Rule:** Game starts only when at least 2 players join!\n\n"
        "Click below to start playing:",
        reply_markup=keyboard
    )

@app_telegram.on_message(filters.command("play"))
async def play_command(client, message):
    game_code = game_manager.create_game(message.from_user.id, message.from_user.first_name, "multiplayer")
    
    web_app_url = f"{FRONTEND_URL}?game_code={game_code}&user_id={message.from_user.id}"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 Open Game", web_app=WebAppInfo(url=web_app_url))],
        [InlineKeyboardButton("📤 Share Game Code", 
         url=f"https://t.me/share/url?url=Join my Snake Ladder game! Code: {game_code}")]
    ])
    
    await message.reply_text(
        f"🎮 **Multiplayer Game Created!**\n\n"
        f"**Game Code:** `{game_code}`\n"
        f"**Players:** 1/4 👥\n"
        f"**Status:** ⏳ Waiting for players...\n\n"
        f"**Game will start when 2 players join!**\n\n"
        f"Share this code with friends:\n"
        f"`{game_code}`",
        reply_markup=keyboard
    )

@app_telegram.on_message(filters.command("join"))
async def join_command(client, message):
    if len(message.command) < 2:
        await message.reply_text("❌ **Usage:** `/join GAMECODE`")
        return
    
    game_code = message.command[1].upper()
    
    success, message_text = game_manager.join_game(game_code, message.from_user.id, message.from_user.first_name)
    
    if success:
        web_app_url = f"{FRONTEND_URL}?game_code={game_code}&user_id={message.from_user.id}"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎮 Play Now", web_app=WebAppInfo(url=web_app_url))]
        ])
        
        await message.reply_text(
            f"✅ **Joined Game Successfully!**\n\n"
            f"**Game Code:** `{game_code}`\n"
            f"Click below to play:",
            reply_markup=keyboard
        )
    else:
        await message.reply_text(f"❌ {message_text}")

@app_telegram.on_callback_query()
async def handle_callbacks(client, callback_query):
    data = callback_query.data
    
    if data == "create_multiplayer":
        await play_command(client, callback_query.message)
    
    elif data == "show_help":
        await callback_query.message.edit_text(
            "📖 **Game Rules:**\n"
            "• 🎲 Roll dice to move\n"
            "• 🐍 Snake head → Go to tail\n" 
            "• 🪜 Ladder bottom → Climb to top\n"
            "• 🏁 Reach exactly 100 to win!\n\n"
            "**Multiplayer:** Starts when 2+ players join",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎮 Start Playing", callback_data="start_playing")]
            ])
        )
    
    elif data == "start_playing":
        await start_command(client, callback_query.message)

def cleanup_games():
    while True:
        try:
            cutoff = datetime.now() - timedelta(hours=2)
            conn = sqlite3.connect('games.db')
            c = conn.cursor()
            c.execute('DELETE FROM games WHERE created_at < ?', (cutoff,))
            conn.commit()
            conn.close()
            
            for game_code in list(game_manager.games.keys()):
                if game_code in game_manager.games and game_manager.games[game_code]['created_at'] < cutoff:
                    del game_manager.games[game_code]
                    
        except Exception as e:
            print(f"Cleanup error: {e}")
        
        time.sleep(3600)

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    print(f"🌐 Starting Flask Server on port {port}...")
    app_flask.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

if __name__ == "__main__":
    print("🚀 Starting Snake Ladder Telegram Game System...")
    
    # Start cleanup thread
    cleanup_thread = threading.Thread(target=cleanup_games, daemon=True)
    cleanup_thread.start()
    
    # Start Flask in separate thread
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
