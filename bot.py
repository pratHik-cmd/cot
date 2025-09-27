from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask, request, jsonify
from flask_cors import CORS
import random
import os

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
        self.status = "waiting"
        self.current_turn = None
        self.moves_history = []
        self.min_players = 2
        
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
            'ready': True
        }
        return True, f"✅ {username} joined the game!"
    
    def remove_player(self, user_id):
        if user_id in self.players:
            username = self.players[user_id]['username']
            del self.players[user_id]
            return True, f"❌ {username} left the game!"
        return False, "Player not found!"
    
    def start_game(self):
        if len(self.players) < self.min_players:
            return False, f"❌ Need at least {self.min_players} players to start!"
        
        if self.status != "waiting":
            return False, "❌ Game has already started!"
        
        self.status = "playing"
        self.current_turn = list(self.players.keys())[0]
        return True, f"🚀 Game started with {len(self.players)} players!"
    
    def make_move(self, user_id, dice_value):
        if self.status != "playing":
            return {"error": "Game is not active"}
        
        if user_id != self.current_turn:
            return {"error": "Not your turn!"}
        
        player = self.players[user_id]
        new_position = player['position'] + dice_value
        
        if new_position > 100:
            return {"error": "Need exact roll to win!"}
        
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
            return {
                "winner": user_id, 
                "new_position": new_position,
                "message": f"🎉 {player['username']} wins the game!"
            }
        
        player_ids = list(self.players.keys())
        current_index = player_ids.index(user_id)
        next_index = (current_index + 1) % len(player_ids)
        self.current_turn = player_ids[next_index]
        
        return {
            "success": True, 
            "new_position": new_position, 
            "next_player": self.current_turn,
            "message": f"🎲 {player['username']} rolled {dice_value}"
        }

# Flask API Routes
@app_flask.route('/')
def serve_game():
    return jsonify({"status": "Server is running", "message": "Snake Ladder Game API"})

@app_flask.route('/api/game_state', methods=['POST'])
def api_game_state():
    try:
        data = request.get_json()
        game_code = data.get('game_code')
        
        if game_code in active_games:
            game = active_games[game_code]
            return jsonify({
                'game_code': game.game_code,
                'players': game.players,
                'status': game.status,
                'current_turn': game.current_turn,
                'players_count': len(game.players),
                'can_start': len(game.players) >= game.min_players
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

# Telegram Bot Handlers
@app_telegram.on_message(filters.command("start"))
async def start_command(client, message):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 Create Game", callback_data="create_game")],
        [InlineKeyboardButton("📖 How to Play", callback_data="show_help")]
    ])
    
    await message.reply_text(
        "🐍 **Snake Ladder Bot** 🎲\n\n"
        "Welcome to the classic Snake Ladder game!\n\n"
        "**Quick Commands:**\n"
        "• `/play` - Create multiplayer game\n"
        "• `/join CODE` - Join existing game\n"
        "• `/leave` - Leave current game\n\n"
        "**Features:**\n"
        "• 2-4 players multiplayer\n"
        "• Real-time gameplay\n"
        "• Snake & Ladder mechanics\n\n"
        "Click below to get started:",
        reply_markup=keyboard
    )

@app_telegram.on_message(filters.command("play"))
async def play_command(client, message):
    try:
        game_code = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=6))
        game = SnakeLadderGame(game_code, message.from_user.id)
        success, message_text = game.add_player(message.from_user.id, message.from_user.first_name)
        
        if success:
            active_games[game_code] = game
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("👥 View Players", callback_data=f"players_{game_code}")],
                [InlineKeyboardButton("🚀 Start Game", callback_data=f"start_{game_code}")],
                [InlineKeyboardButton("❌ Cancel Game", callback_data=f"cancel_{game_code}")]
            ])
            
            await message.reply_text(
                f"🎮 **Game Created Successfully!** ✅\n\n"
                f"**Game Code:** `{game_code}`\n"
                f"**Players:** 1/4 👥\n"
                f"**Status:** Waiting for players...\n\n"
                f"**Share this code with friends:**\n"
                f"`{game_code}`\n\n"
                f"**Friends should use:**\n"
                f"`/join {game_code}`\n\n"
                f"**Minimum 2 players needed to start!**",
                reply_markup=keyboard
            )
        else:
            await message.reply_text(f"❌ {message_text}")
            
    except Exception as e:
        await message.reply_text("❌ Error creating game. Please try again.")

@app_telegram.on_message(filters.command("join"))
async def join_command(client, message):
    if len(message.command) < 2:
        await message.reply_text("❌ **Usage:** `/join GAMECODE`\n**Example:** `/join ABC123`")
        return
    
    game_code = message.command[1].upper()
    
    if game_code not in active_games:
        await message.reply_text("❌ Game not found! Please check the game code.")
        return
    
    game = active_games[game_code]
    
    if game.status != "waiting":
        await message.reply_text("❌ Game has already started! You cannot join now.")
        return
    
    success, message_text = game.add_player(message.from_user.id, message.from_user.first_name)
    
    if success:
        # Player joined successfully
        player_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("👀 View Game", callback_data=f"view_{game_code}")],
            [InlineKeyboardButton("❌ Leave Game", callback_data=f"leave_{game_code}")]
        ])
        
        await message.reply_text(
            f"✅ **Joined Game Successfully!** 🎉\n\n"
            f"**Game Code:** `{game_code}`\n"
            f"**Host:** {game.players[game.host_id]['username']}\n"
            f"**Players:** {len(game.players)}/4 👥\n"
            f"**Status:** {'Ready to start! 🚀' if len(game.players) >= 2 else 'Waiting for more players...'}\n\n"
            f"Wait for the host to start the game!",
            reply_markup=player_keyboard
        )
        
        # Notify host
        host_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🚀 Start Game", callback_data=f"start_{game_code}")],
            [InlineKeyboardButton("👥 View Players", callback_data=f"players_{game_code}")]
        ])
        
        await client.send_message(
            game.host_id,
            f"👤 **{message.from_user.first_name} joined your game!**\n\n"
            f"**Game Code:** {game_code}\n"
            f"**Total players:** {len(game.players)}/4\n"
            f"**Status:** {'Ready to start! ✅' if len(game.players) >= 2 else 'Need more players...'}",
            reply_markup=host_keyboard
        )
    else:
        await message.reply_text(f"❌ {message_text}")

@app_telegram.on_message(filters.command("leave"))
async def leave_command(client, message):
    user_games = []
    for code, game in active_games.items():
        if message.from_user.id in game.players:
            user_games.append((code, game))
    
    if not user_games:
        await message.reply_text("❌ You are not in any active games!")
        return
    
    if len(user_games) == 1:
        game_code, game = user_games[0]
        success, message_text = game.remove_player(message.from_user.id)
        await message.reply_text(message_text)
        
        if game_code in active_games and game.players:
            await client.send_message(
                game.host_id,
                f"👤 **{message.from_user.first_name} left the game!**\n"
                f"Remaining players: {len(game.players)}/4"
            )
    else:
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
    
    if data == "create_game":
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
            "• Host starts the game\n\n"
            "**Requirements:**\n"
            "• Minimum 2 players to start\n"
            "• Maximum 4 players\n",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎮 Create Game", callback_data="create_game")],
                [InlineKeyboardButton("🔙 Back", callback_data="back_start")]
            ])
        )
    
    elif data.startswith("start_"):
        game_code = data.replace("start_", "")
        if game_code in active_games:
            game = active_games[game_code]
            if game.host_id == user_id:
                success, message_text = game.start_game()
                if success:
                    # Notify all players
                    for player_id in game.players:
                        try:
                            await client.send_message(
                                player_id,
                                f"🚀 **Game Started!** 🎮\n\n"
                                f"**Game Code:** {game_code}\n"
                                f"**Players:** {len(game.players)}\n"
                                f"**First turn:** {game.players[game.current_turn]['username']}\n\n"
                                f"Let's play! 🎲"
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
    
    elif data.startswith("players_"):
        game_code = data.replace("players_", "")
        if game_code in active_games:
            game = active_games[game_code]
            players_list = "\n".join([f"• {player['username']}" for player in game.players.values()])
            await callback_query.message.edit_text(
                f"👥 **Players in Game {game_code}**\n\n"
                f"{players_list}\n\n"
                f"**Total:** {len(game.players)}/4 players\n"
                f"**Status:** {game.status}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data=f"view_{game_code}")]
                ])
            )
    
    elif data == "back_start":
        await start_command(client, callback_query.message)
    
    else:
        await callback_query.answer("Button clicked!")

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    print(f"🌐 Starting Flask Server on port {port}...")
    app_flask.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

if __name__ == "__main__":
    print("🚀 Starting Snake Ladder Telegram Game System...")
    print("=" * 50)
    
    import threading
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    import time
    time.sleep(2)
    
    try:
        print("🤖 Starting Telegram Bot...")
        app_telegram.run()
    except Exception as e:
        print(f"❌ Error: {e}")
