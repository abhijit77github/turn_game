"""
Reaction Game - Multiplayer Turn-Based Game API
Uses modular game engine for extensible game support
"""

from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
import jwt
import bcrypt
import sqlite3
import asyncio
import string
import json
from contextlib import contextmanager

# Import game engine modules
from config import game_manager, initialize_games, get_game_config, get_available_games
from room_manager import RoomManager
from game_engine import GameStatus, PlayerStatus

app = FastAPI(title="Reaction Game API - Multi-Game Edition")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
DATABASE = "game.db"

security = HTTPBearer()

# Initialize managers
room_manager = RoomManager()
active_connections: Dict[str, Dict[str, WebSocket]] = {}


# Database setup
@contextmanager
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


# Pydantic models
class UserRegister(BaseModel):
    username: str
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class CreateRoom(BaseModel):
    game_type: str = "number_picker"  # Default to number_picker if not specified


class JoinRoom(BaseModel):
    room_code: str


class GameAction(BaseModel):
    action: Any


class Token(BaseModel):
    access_token: str
    token_type: str


# Helper functions
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    token = credentials.credentials
    payload = decode_token(token)
    return payload.get("sub")


# API Routes

@app.on_event("startup")
async def startup_event():
    init_db()
    initialize_games()


@app.get("/api/games")
async def list_games():
    """Get list of available games"""
    return get_available_games()


@app.post("/api/register", response_model=Token)
async def register(user: UserRegister):
    with get_db() as conn:
        # Check if username exists
        cursor = conn.execute("SELECT id FROM users WHERE username = ?", (user.username,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Username already exists")
        
        # Create user
        password_hash = hash_password(user.password)
        conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (user.username, password_hash)
        )
        conn.commit()
        
        # Create token
        access_token = create_access_token({"sub": user.username})
        return {"access_token": access_token, "token_type": "bearer"}


@app.post("/api/login", response_model=Token)
async def login(user: UserLogin):
    with get_db() as conn:
        cursor = conn.execute(
            "SELECT password_hash FROM users WHERE username = ?",
            (user.username,)
        )
        result = cursor.fetchone()
        
        if not result or not verify_password(user.password, result[0]):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        access_token = create_access_token({"sub": user.username})
        return {"access_token": access_token, "token_type": "bearer"}


@app.post("/api/room/create")
async def create_room(data: CreateRoom = CreateRoom(), username: str = Depends(get_current_user)):
    """Create a new game room"""
    
    # Get game configuration
    try:
        game_config = get_game_config(data.game_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Create game engine instance
    game_engine = game_manager.create_game_instance(data.game_type, game_config)
    if not game_engine:
        raise HTTPException(status_code=400, detail="Failed to create game instance")
    
    # Create room
    room = room_manager.create_room(username, data.game_type, game_engine)
    
    # Initialize game with players
    await game_engine.initialize_game([username], room.code)
    
    return {
        "room_code": room.code,
        "game_type": data.game_type,
        "max_players": room.max_players,
        "creator": username
    }


@app.post("/api/room/join")
async def join_room(data: JoinRoom, username: str = Depends(get_current_user)):
    """Join an existing game room"""
    
    room = room_manager.get_room(data.room_code)
    
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    if room.game_started:
        raise HTTPException(status_code=400, detail="Game already started")
    
    if not room.add_player(username):
        raise HTTPException(status_code=400, detail="Room is full or player already in room")
    
    # Update game engine with new players
    await room.game_engine.initialize_game(room.players, room.code)
    
    # Notify all players
    await broadcast_to_room(room.code, {
        "type": "player_joined",
        "username": username,
        "players": room.players,
        "player_count": len(room.players)
    })
    
    return {
        "room_code": room.code,
        "game_type": room.game_type,
        "players": room.players,
        "creator": room.creator
    }


async def broadcast_to_room(room_code: str, message: dict):
    """Broadcast message to all players in a room"""
    if room_code in active_connections:
        disconnected = []
        for username, websocket in active_connections[room_code].items():
            try:
                await websocket.send_json(message)
            except Exception:
                disconnected.append(username)
        
        # Clean up disconnected websockets
        for username in disconnected:
            del active_connections[room_code][username]


@app.websocket("/ws/{room_code}/{username}")
async def websocket_endpoint(websocket: WebSocket, room_code: str, username: str):
    await websocket.accept()
    
    room_code = room_code.upper()
    room = room_manager.get_room(room_code)
    
    if not room:
        await websocket.send_json({"type": "error", "message": "Room not found"})
        await websocket.close()
        return
    
    if username not in room.players:
        await websocket.send_json({"type": "error", "message": "Not in room"})
        await websocket.close()
        return
    
    # Store connection
    if room_code not in active_connections:
        active_connections[room_code] = {}
    active_connections[room_code][username] = websocket
    
    # Send current room state
    room_state_msg = {
        "type": "room_state",
        "room": room.get_info()
    }
    
    # If game has ended, send game state
    if not room.game_started and room.game_engine.game_state:
        game_state = room.game_engine.game_state
        if game_state.status == GameStatus.FINISHED:
            room_state_msg["game_ended"] = {
                "winner": game_state.winner,
                "can_restart": True
            }
    
    await websocket.send_json(room_state_msg)
    
    try:
        while True:
            data = await websocket.receive_json()
            await handle_websocket_message(room_code, username, data)
    except WebSocketDisconnect:
        if room_code in active_connections and username in active_connections[room_code]:
            del active_connections[room_code][username]


async def handle_websocket_message(room_code: str, username: str, data: dict):
    """Handle incoming WebSocket messages"""
    
    room = room_manager.get_room(room_code)
    if not room:
        return
    
    message_type = data.get("type")
    print(f"Received message type: {message_type} from {username} in room {room_code}")
    print(f"Message data: {data}")
    
    if message_type == "start_game":
        if username != room.creator:
            print(f"User {username} is not room creator {room.creator}")
            return
        
        if room.game_started:
            print(f"Game already started in room {room_code}")
            return
        
        if not room.can_start():
            print(f"Cannot start game in room {room_code}")
            await active_connections[room_code][username].send_json({
                "type": "error",
                "message": f"Cannot start game"
            })
            return
        
        print(f"Starting game in room {room_code} with players: {room.players}")
        
        # Initialize game and start first turn
        room.game_started = True
        game_engine = room.game_engine
        
        # Get player usernames for initialization
        player_names = [p for p in room.players]
        print(f"Initializing game with players: {player_names}")
        await game_engine.initialize_game(player_names, room.code)
        print(f"Game initialized. Game state: {game_engine.game_state}")
        
        # Create turn timer task and store it
        timer_task = asyncio.create_task(run_turn_timer(room_code, 0))
        if not hasattr(room, '_timer_task'):
            room._timer_task = None
        room._timer_task = timer_task
        
        # Get turn data and broadcast
        turn_data = await game_engine.get_turn_data()
        print(f"Turn data from game engine: {turn_data}")
        turn_data["type"] = "game_started"
        
        print(f"Broadcasting game_started: {turn_data}")
        await broadcast_to_room(room_code, turn_data)
    
    elif message_type == "make_choice":
        if not room.game_started:
            print(f"Game not started for room {room_code}")
            return
        
        game_engine = room.game_engine
        action = data.get("action")
        
        # Try to convert action to int if needed
        if action is not None:
            try:
                action = int(action)
            except (ValueError, TypeError):
                pass
        
        print(f"Player {username} making choice: {action} (type: {type(action)})")
        
        # Cancel current timer before processing action
        if hasattr(room, '_timer_task') and room._timer_task:
            try:
                room._timer_task.cancel()
            except:
                pass
            room._timer_task = None
        
        # Process action and get events
        try:
            result = await game_engine.process_turn_action(username, action)
            if not result.get("success"):
                await broadcast_to_room(room_code, {
                    "type": "error",
                    "message": "Invalid action"
                })
                
                # Send next_turn to keep the player and allow retry
                turn_data = await game_engine.get_turn_data()
                turn_data["type"] = "next_turn"
                
                # Restart timer for retry
                timer_task = asyncio.create_task(run_turn_timer(room_code, game_engine.game_state.current_turn.turn_number))
                room._timer_task = timer_task
                
                await broadcast_to_room(room_code, turn_data)
                return
        except Exception as e:
            print(f"Error processing action: {e}")
            import traceback
            traceback.print_exc()
            await broadcast_to_room(room_code, {
                "type": "error",
                "message": str(e)
            })
            
            # Send next_turn to keep the player and allow retry
            turn_data = await game_engine.get_turn_data()
            turn_data["type"] = "next_turn"
            
            # Restart timer for retry
            timer_task = asyncio.create_task(run_turn_timer(room_code, game_engine.game_state.current_turn.turn_number))
            room._timer_task = timer_task
            
            await broadcast_to_room(room_code, turn_data)
            return
        
        # Send all events at once with timing metadata
        events = result.get("events", [])
        
        # Broadcast all events immediately WITH current board state
        # Client will handle animation timing based on event.time metadata
        await broadcast_to_room(room_code, {
            "type": "game_events",
            "events": events,
            "board": game_engine.game_state.game_data.get("board", [])
        })
        
        # Don't wait on server - immediately advance to next turn
        # Client handles animation timing, server doesn't need to block
        await advance_game_turn(room_code)
    
    elif message_type == "exit_game":
        await handle_player_exit(room_code, username)
    
    elif message_type == "restart_game":
        if username != room.creator:
            return
        
        if room.game_engine.game_state is None:
            return
        
        room.game_started = True
        game_engine = room.game_engine
        
        # Re-initialize game
        await game_engine.initialize_game(room.players, room.code)
        
        # Create new turn timer and store it
        timer_task = asyncio.create_task(run_turn_timer(room_code, 0))
        if not hasattr(room, '_timer_task'):
            room._timer_task = None
        room._timer_task = timer_task
        
        # Broadcast
        turn_data = await game_engine.get_turn_data()
        turn_data["type"] = "game_started"
        
        await broadcast_to_room(room_code, turn_data)


async def run_turn_timer(room_code: str, turn_number: int):
    """Run timer for current turn"""
    room = room_manager.get_room(room_code)
    if not room:
        return
    
    game_engine = room.game_engine
    turn_time = game_engine.config.turn_time
    
    try:
        await asyncio.sleep(turn_time)
    except asyncio.CancelledError:
        return
    
    # Re-check room after sleep (in case it was deleted)
    room = room_manager.get_room(room_code)
    if not room or not room.game_started:
        return
    
    # Verify this timer is still the active one
    if hasattr(room, '_timer_task') and room._timer_task and room._timer_task != asyncio.current_task():
        return
    
    # Verify turn number hasn't changed
    if game_engine.game_state.current_turn.turn_number != turn_number:
        return
    
    # Auto-play
    current_player = game_engine.game_state.players[game_engine.game_state.current_turn.current_player_index]
    auto_action = await game_engine.handle_auto_play()
    
    await game_engine.process_turn_action(current_player.username, auto_action)
    
    await broadcast_to_room(room_code, {
        "type": "auto_choice",
        "player": current_player.username,
        "action": auto_action
    })
    
    # Clear timer reference since we're advancing
    room._timer_task = None
    
    await advance_game_turn(room_code)


async def advance_game_turn(room_code: str):
    """Advance to next turn"""
    room = room_manager.get_room(room_code)
    if not room:
        return
    
    game_engine = room.game_engine
    
    # Cancel any existing timer before proceeding
    if hasattr(room, '_timer_task') and room._timer_task:
        try:
            room._timer_task.cancel()
        except:
            pass
        room._timer_task = None
    
    # Check if game continues
    if not await game_engine.advance_turn():
        # Game ended
        room.game_started = False
        
        await broadcast_to_room(room_code, {
            "type": "game_ended",
            "winner": game_engine.game_state.winner,
            "can_restart": True,
            "game_status": game_engine.get_game_status(),
            "board": game_engine.game_state.game_data.get("board", []),
            "player_colors": game_engine.game_state.game_data.get("player_colors", {})
        })
    else:
        # Send next turn data
        turn_data = await game_engine.get_turn_data()
        turn_data["type"] = "next_turn"
        
        # Create new timer and store it
        timer_task = asyncio.create_task(run_turn_timer(room_code, game_engine.game_state.current_turn.turn_number))
        room._timer_task = timer_task
        
        await broadcast_to_room(room_code, turn_data)


async def handle_player_exit(room_code: str, username: str):
    """Handle player exit from game"""
    room = room_manager.get_room(room_code)
    if not room:
        return
    
    room.remove_player(username)
    
    # Remove from connections
    if room_code in active_connections and username in active_connections[room_code]:
        del active_connections[room_code][username]
    
    # Delete empty rooms
    if len(room.players) == 0:
        room_manager.delete_room(room_code)
        return
    
    # If creator left, assign new creator
    if username == room.creator and room.players:
        room.creator = room.players[0]
    
    # If game is running, handle player disconnect
    if room.game_started:
        await room.game_engine.handle_player_disconnect(username)
        
        # Check minimum players
        if len(room.players) < room.game_engine.config.min_players:
            room.game_started = False
            await broadcast_to_room(room_code, {
                "type": "game_ended",
                "reason": "Not enough players"
            })
    
    await broadcast_to_room(room_code, {
        "type": "player_left",
        "username": username,
        "players": room.players,
        "creator": room.creator
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main_new:app", host="192.168.0.6", port=8000, reload=True)
