from flask import Flask, request, jsonify
from flask_cors import CORS
import random
import os
import uuid
import base64
from flask_socketio import SocketIO, emit, join_room, leave_room

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')
CORS(app)

# Use eventlet for better WebSocket performance if available
try:
    import eventlet
    eventlet.monkey_patch()
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet', logger=True, engineio_logger=True)
except ImportError:
    socketio = SocketIO(app, cors_allowed_origins="*", logger=True, engineio_logger=True)

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
        'game_code': game.game_code
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

@app.route('/api/health')
def health():
    return jsonify({'status': 'healthy', 'active_games': len(games)})

# WebSocket Events for Voice Chat
@socketio.on('connect')
def handle_connect():
    print('Client connected:', request.sid)
    emit('connected', {'message': 'Connected to voice server', 'sid': request.sid})

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected:', request.sid)

@socketio.on('join_voice_room')
def handle_join_voice_room(data):
    game_code = data.get('game_code')
    user_id = data.get('user_id')
    username = data.get('username')
    
    if game_code and game_code in games:
        room = f"voice_{game_code}"
        join_room(room)
        emit('user_joined_voice', {
            'user_id': user_id,
            'username': username,
            'message': f'{username} joined the voice chat',
            'sid': request.sid
        }, room=room)
        print(f"User {username} joined voice room: {room}")

@socketio.on('leave_voice_room')
def handle_leave_voice_room(data):
    game_code = data.get('game_code')
    user_id = data.get('user_id')
    username = data.get('username')
    
    if game_code and game_code in games:
        room = f"voice_{game_code}"
        leave_room(room)
        emit('user_left_voice', {
            'user_id': user_id,
            'username': username,
            'message': f'{username} left the voice chat'
        }, room=room)
        print(f"User {username} left voice room: {room}")

@socketio.on('voice_data')
def handle_voice_data(data):
    game_code = data.get('game_code')
    user_id = data.get('user_id')
    username = data.get('username')
    audio_data = data.get('audio_data')
    
    if game_code and game_code in games:
        room = f"voice_{game_code}"
        # Send to everyone in room except sender
        emit('voice_stream', {
            'user_id': user_id,
            'username': username,
            'audio_data': audio_data,
            'timestamp': data.get('timestamp')
        }, room=room, include_self=False)
        print(f"Voice data from {username} to room {room}")

@socketio.on('voice_status')
def handle_voice_status(data):
    game_code = data.get('game_code')
    user_id = data.get('user_id')
    username = data.get('username')
    is_speaking = data.get('is_speaking')
    
    if game_code and game_code in games:
        room = f"voice_{game_code}"
        emit('user_voice_status', {
            'user_id': user_id,
            'username': username,
            'is_speaking': is_speaking
        }, room=room)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True)

