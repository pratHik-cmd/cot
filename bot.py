from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from flask import Flask, request, jsonify
from flask_cors import CORS
import random
import os
import asyncio

# Flask App for Frontend-Backend Communication
app_flask = Flask(__name__)
CORS(app_flask)

# Telegram Bot Configuration
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
        self.status = "waiting"  # waiting, playing, finished
        self.current_turn = None
        self.moves_history = []
        self.min_players = 2  # Minimum players required
        
        self.snakes = {16: 6, 47: 26, 49: 11, 56: 53, 62: 19, 64: 60, 87: 24, 93: 73, 95: 75, 98: 78}
        self.ladders = {1: 38, 4: 14, 9: 31, 21: 42, 28: 84, 36: 44, 51: 67, 71: 91, 80: 100}
    
    def add_player(self, user_id, username):
        if len(self.players) >= 4:
            return False, "Game is full! Maximum 4 players allowed."
        
        if user_id in self.players:
            return False, "You are already in this game!"
        
        color_options = ['#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4']
        self.players[user_id] = {
            'username': username,
            'position': 1,
            'color': color_options[len(self.players)],
            'ready': False
        }
        return True, f"{username} joined the game!"
    
    def remove_player(self, user_id):
        if user_id in self.players:
            username = self.players[user_id]['username']
            del self.players[user_id]
            return True, f"{username} left the game!"
        return False, "Player not found!"
    
    def start_game(self):
        if len(self.players) < self.min_players:
            return False, f"Need at least {self.min_players} players to start!"
        
        if self.status != "waiting":
            return False, "Game has already started!"
        
        self.status = "playing"
        self.current_turn = list(self.players.keys())[0]
        return True, f"Game started with {len(self.players)} players!"
    
    def make_move(self, user_id, dice_value):
        if self.status != "playing":
            return {"error": "Game is not active"}
        
        if user_id != self.current_turn:
            return {"error": "Not your turn!"}
        
        player = self.players[user_id]
        new_position = player['position'] + dice_value
        
        if new_position > 100:
            return {"error": "Need exact roll to win! Stay where you are."}
        
        move_info = {
            'player': user_id,
            'dice_value': dice_value,
            'from_position': player['position'],
            'to_position': new_position,
            'special_move': None
        }
        
        # Check for snakes and ladders
        if new_position in self.snakes:
            move_info['special_move'] = f"snake_{new_position}_{self.snakes[new_position]}"
            new_position = self.snakes[new_position]
        elif new_position in self.ladders:
            move_info['special_move'] = f"ladder_{new_position}_{self.ladders[new_position]}"
            new_position = self.ladders[new_position]
        
        player['position'] = new_position
        self.moves_history.append(move_info)
        
        # Check for winner
        if new_position == 100:
            self.status = "finished"
            return {
                "winner": user_id, 
                "new_position": new_position,
                "message": f"🎉 {player['username']} wins the game!"
            }
        
        # Move to next player
        player_ids = list(self.players.keys())
        current_index = player_ids.index(user_id)
        next_index = (current_index + 1) % len(player_ids)
        self.current_turn = player_ids[next_index]
        
        return {
            "success": True, 
            "new_position": new_position, 
            "next_player": self.current_turn,
            "message": f"🎲 {player['username']} rolled {dice_value}, moved to {new_position}"
        }
    
    def get_game_info(self):
        return {
            'game_code': self.game_code,
            'host_id': self.host_id,
            'players': self.players,
            'status': self.status,
            'current_turn': self.current_turn,
            'players_count': len(self.players),
            'min_players': self.min_players,
            'can_start': len(self.players) >= self.min_players and self.status == "waiting"
        }

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
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🐍 Snake Ladder Game</h1>
            <p>🚀 Backend is running successfully!</p>
            <p>💡 Use your Telegram bot to play the game</p>
            <p>🤖 Send /start to @Prarizz_bot</p>
        </div>
    </body>
    </html>
    """

@app_flask.route('/api/game_state', methods=['POST'])
def api_game_state():
    try:
        data = request.get_json()
        game_code = data.get('game_code')
        
        if game_code in active_games:
            game = active_games[game_code]
            return jsonify(game.get_game_info())
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
        user_id = data.get('user_id')
        username = data.get('username')
        
        game_code = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=6))
        game = SnakeLadderGame(game_code, user_id)
        success, message = game.add_player(int(user_id), username)
        
        if success:
            active_games[game_code] = game
            return jsonify({
                'game_code': game_code, 
                'status': 'created',
                'message': message
            })
        else:
            return jsonify({'error': message})
    except Exception as e:
        return jsonify({'error': str(e)})

@app_flask.route('/api/start_game', methods=['POST'])
def api_start_game():
    try:
        data = request.get_json()
        game_code = data.get('game_code')
        user_id = data.get('user_id')
        
        if game_code in active_games:
            game = active_games[game_code]
            if game.host_id != int(user_id):
                return jsonify({'error': 'Only host can start the game!'})
            
            success, message = game.start_game()
            return jsonify({'success': success, 'message': message})
        else:
            return jsonify({'error': 'Game not found'})
    except Exception as e:
        return jsonify({'error': str(e)})

# Telegram Bot Handlers
@app_telegram.on_message(filters.command("start"))
async def start_command(client, message):
    web_app_url = f"https://pratHik-cmd.github.io/snake-ladder-game/index.html?user_id={message.from_user.id}"
    
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
        "• 👥 Play with friends (2-4 players)\n"
        "• 🎲 Smooth gameplay\n"
        "• 📱 Mobile optimized\n\n"
        "**Multiplayer Rules:**\n"
        "• Minimum 2 players required\n"
        "• Host must start the game\n"
        "• Turns go clockwise\n\n"
        "Click below to start playing:",
        reply_markup=keyboard
    )

@app_telegram.on_message(filters.command("play"))
async def play_command(client, message):
    # Create new game
    game_code = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=6))
    game = SnakeLadderGame(game_code, message.from_user.id)
    success, message_text = game.add_player(message.from_user.id, message.from_user.first_name)
    
    if success:
        active_games[game_code] = game
        
        # Create invitation message
        invite_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎮 Join Game", callback_data=f"join_{game_code}")],
            [InlineKeyboardButton("🚀 Start Game", callback_data=f"start_{game_code}")],
            [InlineKeyboardButton("📤 Share Invite", url=f"https://t.me/share/url?url=Join my Snake Ladder game! Use code: {game_code}")]
        ])
        
        await message.reply_text(
            f"🎮 **Multiplayer Game Created!** 🐍\n\n"
            f"**Host:** {message.from_user.first_name}\n"
            f"**Game Code:** `{game_code}`\n"
            f"**Players:** 1/4 👥\n"
            f"**Status:** Waiting for players...\n\n"
            f"**Invite friends using:**\n"
            f"• Game Code: `{game_code}`\n"
            f"• Command: `/join {game_code}`\n\n"
            f"**Minimum 2 players needed to start!**",
            reply_markup=invite_keyboard
        )
    else:
        await message.reply_text(f"❌ {message_text}")

@app_telegram.on_message(filters.command("join"))
async def join_command(client, message):
    if len(message.command) < 2:
        await message.reply_text("❌ Usage: `/join GAMECODE`\nExample: `/join ABC123`")
        return
    
    game_code = message.command[1].upper()
    
    if game_code not in active_games:
        await message.reply_text("❌ Game not found! Check the game code.")
        return
    
    game = active_games[game_code]
    
    if game.status != "waiting":
        await message.reply_text("❌ Game has already started!")
        return
    
    success, message_text = game.add_player(message.from_user.id, message.from_user.first_name)
    
    if success:
        # Update host about new player
        game_url = f"https://pratHik-cmd.github.io/snake-ladder-game/index.html?game_code={game_code}&user_id={message.from_user.id}"
        
        player_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎮 Play Now", web_app=WebAppInfo(url=game_url))],
            [InlineKeyboardButton("📤 Share Game", url=f"https://t.me/share/url?url=Join our Snake Ladder game! Code: {game_code}")]
        ])
        
        await message.reply_text(
            f"✅ **Joined Game Successfully!** 🎉\n\n"
            f"**Game Code:** `{game_code}`\n"
            f"**Host:** {game.players[game.host_id]['username']}\n"
            f"**Players:** {len(game.players)}/4 👥\n"
            f"**Status:** { 'Ready to start! 🚀' if len(game.players) >= 2 else 'Waiting for more players...' }\n\n"
            f"Host will start the game when ready!",
            reply_markup=player_keyboard
        )
        
        # Notify host about new player
        host_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🚀 Start Game", callback_data=f"start_{game_code}")],
            [InlineKeyboardButton("👀 View Players", callback_data=f"players_{game_code}")]
        ])
        
        await client.send_message(
            game.host_id,
            f"👤 **{message.from_user.first_name} joined your game!**\n\n"
            f"**Game Code:** {game_code}\n"
            f"**Total players:** {len(game.players)}/4\n"
            f"**Status:** { 'Ready to start! ✅' if len(game.players) >= 2 else 'Need more players...' }",
            reply_markup=host_keyboard
        )
    else:
        await message.reply_text(f"❌ {message_text}")

@app_telegram.on_message(filters.command("leave"))
async def leave_command(client, message):
    # Find games where user is playing
    user_games = []
    for code, game in active_games.items():
        if message.from_user.id in game.players:
            user_games.append((code, game))
    
    if not user_games:
        await message.reply_text("❌ You are not in any active games!")
        return
    
    if len(user_games) == 1:
        # Leave the single game
        game_code, game = user_games[0]
        success, message_text = game.remove_player(message.from_user.id)
        await message.reply_text(f"✅ {message_text}")
        
        # Notify host if game still exists
        if game_code in active_games and game.players:
            await client.send_message(
                game.host_id,
                f"👤 **{message.from_user.first_name} left the game!**\n"
                f"Remaining players: {len(game.players)}/4"
            )
    else:
        # Let user choose which game to leave
        keyboard_buttons = []
        for game_code, game in user_games:
            keyboard_buttons.append([InlineKeyboardButton(
                f"Leave {game_code} ({len(game.players)} players)", 
                callback_data=f"leave_{game_code}"
            )])
        
        keyboard = InlineKeyboardMarkup(keyboard_buttons)
        await message.reply_text("🎮 **Which game do you want to leave?**", reply_markup=keyboard)

@app_telegram.on_callback_query()
async def handle_callbacks(client, callback_query):
    data = callback_query.data
    user_id = callback_query.from_user.id
    
    if data == "create_multiplayer":
        await play_command(client, callback_query.message)
    
    elif data == "show_help":
        await callback_query.message.edit_text(
            "📖 **How to Play Snake Ladder** 🐍\n\n"
            "**Game Rules:**\n"
            "• 🎲 Roll dice to move forward\n"
            "• 🐍 Land on snake head → Go to tail\n"
            "• 🪜 Land on ladder bottom → Climb to top\n"
            "• 🏁 First to reach exactly 100 wins!\n\n"
            "**Multiplayer Commands:**\n"
            "• `/play` - Create new game\n"
            "• `/join CODE` - Join existing game\n"
            "• `/leave` - Leave current game\n"
            "• Host uses Start button to begin\n\n"
            "**Requirements:**\n"
            "• Minimum 2 players to start\n"
            "• Maximum 4 players\n"
            "• Host controls game start",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎮 Create Game", callback_data="create_multiplayer")],
                [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
            ])
        )
    
    elif data.startswith("join_"):
        game_code = data.replace("join_", "")
        if game_code in active_games:
            game = active_games[game_code]
            if game.status == "waiting" and len(game.players) < 4:
                success, message_text = game.add_player(user_id, callback_query.from_user.first_name)
                if success:
                    await callback_query.answer(f"Joined game {game_code}!")
                    await callback_query.message.edit_text(
                        f"✅ **Joined Game {game_code}**\n\n"
                        f"Players: {len(game.players)}/4\n"
                        f"Waiting for host to start...",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🎮 Play", web_app=WebAppInfo(
                                url=f"https://pratHik-cmd.github.io/snake-ladder-game/index.html?game_code={game_code}&user_id={user_id}"
                            ))]
                        ])
                    )
                else:
                    await callback_query.answer(message_text, show_alert=True)
            else:
                await callback_query.answer("Game is full or already started!", show_alert=True)
        else:
            await callback_query.answer("Game not found!", show_alert=True)
    
    elif data.startswith("start_"):
        game_code = data.replace("start_", "")
        if game_code in active_games:
            game = active_games[game_code]
            if game.host_id == user_id:
                success, message_text = game.start_game()
                if success:
                    # Notify all players
                    game_url = f"https://pratHik-cmd.github.io/snake-ladder-game/index.html?game_code={game_code}"
                    for player_id in game.players:
                        try:
                            await client.send_message(
                                player_id,
                                f"🚀 **Game Started!** 🎮\n\n"
                                f"Game Code: {game_code}\n"
                                f"Players: {len(game.players)}\n"
                                f"First turn: {game.players[game.current_turn]['username']}",
                                reply_markup=InlineKeyboardMarkup([
                                    [InlineKeyboardButton("🎮 Play Now", web_app=WebAppInfo(url=f"{game_url}&user_id={player_id}"))]
                                ])
                            )
                        except:
                            continue
                    await callback_query.answer("Game started! Notified all players.")
                else:
                    await callback_query.answer(message_text, show_alert=True)
            else:
                await callback_query.answer("Only host can start the game!", show_alert=True)
        else:
            await callback_query.answer("Game not found!", show_alert=True)
    
    elif data == "start_playing":
        await start_command(client, callback_query.message)
    
    elif data == "back_to_start":
        await start_command(client, callback_query.message)

def run_flask():
    """Run Flask server"""
    port = int(os.environ.get("PORT", 5000))
    print(f"🌐 Starting Flask Server on port {port}...")
    app_flask.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

if __name__ == "__main__":
    print("🚀 Starting Snake Ladder Telegram Game System...")
    print("=" * 50)
    
    # Start Flask server
    import threading
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # Wait for Flask to start
    import time
    time.sleep(3)
    
    # Start Telegram bot
    try:
        print("🤖 Starting Telegram Bot...")
        app_telegram.run()
    except Exception as e:
        print(f"❌ Error: {e}")
