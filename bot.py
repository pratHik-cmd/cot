from flask import Flask, request, jsonify
from flask_cors import CORS
import random
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Game Storage
games = {}

class SnakeLadderGame:
    def __init__(self, game_code, host_id, host_name):
        self.game_code = game_code
        self.host_id = host_id
        self.players = {}
        self.status = "waiting"
        self.current_turn = None
        self.max_players = 2
        self.chat_messages = []  # Chat storage
        self.voice_messages = []  # Voice messages storage
        
        self.snakes = {16: 6, 47: 26, 49: 11, 56: 53, 62: 19, 64: 60, 87: 24, 93: 73, 95: 75, 98: 78}
        self.ladders = {1: 38, 4: 14, 9: 31, 21: 42, 28: 84, 36: 44, 51: 67, 71: 91, 80: 100}
        
        self.add_player(host_id, host_name)
    
    def add_player(self, user_id, username):
        if len(self.players) >= self.max_players:
            return False, "Game is full! Only 2 players allowed."
        
        if str(user_id) in self.players:
            return False, "You are already in this game!"
        
        color_options = ['#ff6b6b', '#4ecdc4']
        self.players[str(user_id)] = {
            'username': username,
            'position': 1,
            'color': color_options[len(self.players)],
            'ready': True
        }
        
        if len(self.players) == 2:
            self.status = "playing"
            player_ids = list(self.players.keys())
            self.current_turn = player_ids[0]
        
        return True, "Joined successfully"
    
    def make_move(self, user_id, dice_value):
        if self.status != "playing":
            return {"error": "Game is not active"}
        
        if str(user_id) != str(self.current_turn):
            return {"error": "Not your turn!"}
        
        player = self.players[str(user_id)]
        new_position = player['position'] + dice_value
        
        if new_position > 100:
            return {"error": "Need exact roll to win!"}
        
        if new_position in self.snakes:
            new_position = self.snakes[new_position]
        elif new_position in self.ladders:
            new_position = self.ladders[new_position]
        
        player['position'] = new_position
        
        if new_position == 100:
            self.status = "finished"
            return {"winner": user_id, "new_position": new_position}
        
        player_ids = list(self.players.keys())
        current_index = player_ids.index(str(user_id))
        next_index = (current_index + 1) % len(player_ids)
        self.current_turn = player_ids[next_index]
        
        return {
            "success": True, 
            "new_position": new_position, 
            "next_player": self.current_turn,
            "message": f"{player['username']} rolled {dice_value} and moved to {new_position}"
        }
    
    def add_chat_message(self, user_id, message, message_type="text"):
        if str(user_id) not in self.players:
            return False
        
        player = self.players[str(user_id)]
        chat_message = {
            'user_id': user_id,
            'username': player['username'],
            'message': message,
            'type': message_type,
            'timestamp': datetime.now().isoformat()
        }
        
        self.chat_messages.append(chat_message)
        # Keep only last 50 messages
        if len(self.chat_messages) > 50:
            self.chat_messages = self.chat_messages[-50:]
        
        return True
    
    def add_voice_message(self, user_id, audio_url, duration):
        if str(user_id) not in self.players:
            return False
        
        player = self.players[str(user_id)]
        voice_message = {
            'user_id': user_id,
            'username': player['username'],
            'audio_url': audio_url,
            'duration': duration,
            'type': 'voice',
            'timestamp': datetime.now().isoformat()
        }
        
        self.voice_messages.append(voice_message)
        # Keep only last 20 voice messages
        if len(self.voice_messages) > 20:
            self.voice_messages = self.voice_messages[-20:]
        
        return True

# API Routes
@app.route('/')
def home():
    return jsonify({"status": "Snake Ladder API", "message": "Backend is running!"})

@app.route('/api/create_game', methods=['POST'])
def create_game():
    data = request.get_json()
    user_id = data.get('user_id')
    username = data.get('username', 'Player')
    
    game_code = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=6))
    game = SnakeLadderGame(game_code, user_id, username)
    games[game_code] = game
    
    return jsonify({
        'game_code': game_code,
        'status': 'created',
        'message': 'Game created successfully!'
    })

@app.route('/api/join_game', methods=['POST'])
def join_game():
    data = request.get_json()
    game_code = data.get('game_code')
    user_id = data.get('user_id')
    username = data.get('username', 'Player')
    
    if game_code not in games:
        return jsonify({'success': False, 'error': 'Game not found'})
    
    game = games[game_code]
    success, message = game.add_player(user_id, username)
    
    return jsonify({
        'success': success,
        'error': None if success else message,
        'game_status': game.status
    })

@app.route('/api/game_state', methods=['POST'])
def game_state():
    data = request.get_json()
    game_code = data.get('game_code')
    
    if game_code not in games:
        return jsonify({'error': 'Game not found'})
    
    game = games[game_code]
    
    return jsonify({
        'players': game.players,
        'current_turn': game.current_turn,
        'status': game.status,
        'game_code': game.game_code,
        'chat_messages': game.chat_messages[-20:],  # Last 20 messages
        'voice_messages': game.voice_messages[-10:]  # Last 10 voice messages
    })

@app.route('/api/make_move', methods=['POST'])
def make_move():
    data = request.get_json()
    game_code = data.get('game_code')
    user_id = data.get('user_id')
    dice_value = data.get('dice_value')
    
    if game_code not in games:
        return jsonify({'error': 'Game not found'})
    
    game = games[game_code]
    result = game.make_move(user_id, dice_value)
    
    return jsonify(result)

@app.route('/api/send_message', methods=['POST'])
def send_message():
    data = request.get_json()
    game_code = data.get('game_code')
    user_id = data.get('user_id')
    message = data.get('message')
    message_type = data.get('type', 'text')
    
    if game_code not in games:
        return jsonify({'success': False, 'error': 'Game not found'})
    
    game = games[game_code]
    success = game.add_chat_message(user_id, message, message_type)
    
    return jsonify({'success': success})

@app.route('/api/send_voice', methods=['POST'])
def send_voice():
    data = request.get_json()
    game_code = data.get('game_code')
    user_id = data.get('user_id')
    audio_url = data.get('audio_url')
    duration = data.get('duration', 0)
    
    if game_code not in games:
        return jsonify({'success': False, 'error': 'Game not found'})
    
    game = games[game_code]
    success = game.add_voice_message(user_id, audio_url, duration)
    
    return jsonify({'success': success})

@app.route('/api/health')
def health():
    return jsonify({'status': 'healthy', 'active_games': len(games)})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
