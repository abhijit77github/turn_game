from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, Dict, List
from datetime import datetime, timedelta
import jwt
import bcrypt
import sqlite3
import asyncio
import random
import string
import json
from contextlib import contextmanager

app = FastAPI(title="Reaction Game API")

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
MAX_PLAYERS = 6
MIN_PLAYERS = 2
TURN_TIME_SECONDS = 15
MAX_TURNS = 5
DATABASE = "game.db"

security = HTTPBearer()


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
    pass


class JoinRoom(BaseModel):
    room_code: str


class GameChoice(BaseModel):
    choice: int


class Token(BaseModel):
    access_token: str
    token_type: str


# In-memory storage for rooms and games
rooms: Dict[str, dict] = {}
active_connections: Dict[str, Dict[str, WebSocket]] = {}


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


def generate_room_code() -> str:
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


def generate_choices() -> List[int]:
    return [random.randint(-100, 100) for _ in range(5)]


# API Routes
@app.on_event("startup")
async def startup_event():
    init_db()


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
async def create_room(username: str = Depends(get_current_user)):
    room_code = generate_room_code()
    
    rooms[room_code] = {
        "code": room_code,
        "creator": username,
        "players": [username],
        "game_started": False,
        "game_state": None,
        "max_players": MAX_PLAYERS,
        "created_at": datetime.utcnow().isoformat()
    }
    
    active_connections[room_code] = {}
    
    return {
        "room_code": room_code,
        "max_players": MAX_PLAYERS,
        "creator": username
    }


@app.post("/api/room/join")
async def join_room(data: JoinRoom, username: str = Depends(get_current_user)):
    room_code = data.room_code.upper()
    
    if room_code not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    
    room = rooms[room_code]
    
    if room["game_started"]:
        raise HTTPException(status_code=400, detail="Game already started")
    
    if len(room["players"]) >= MAX_PLAYERS:
        raise HTTPException(status_code=400, detail="Room is full")
    
    if username in room["players"]:
        return {"message": "Already in room", "room_code": room_code}
    
    room["players"].append(username)
    
    # Notify all players in the room
    await broadcast_to_room(room_code, {
        "type": "player_joined",
        "username": username,
        "players": room["players"],
        "player_count": len(room["players"])
    })
    
    return {
        "room_code": room_code,
        "players": room["players"],
        "creator": room["creator"]
    }


async def broadcast_to_room(room_code: str, message: dict):
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
    
    if room_code not in rooms:
        await websocket.send_json({"type": "error", "message": "Room not found"})
        await websocket.close()
        return
    
    room = rooms[room_code]
    
    if username not in room["players"]:
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
        "room": {
            "code": room_code,
            "creator": room["creator"],
            "players": room["players"],
            "game_started": room["game_started"],
            "max_players": room["max_players"]
        }
    }
    
    # If game has ended, send the game ended state as well
    if not room["game_started"] and room.get("game_state"):
        game_state = room["game_state"]
        if len(game_state.get("player_choices", [])) > 0:
            total_sum = sum(choice["choice"] for choice in game_state["player_choices"])
            winner_index = abs(total_sum) % len(room["players"])
            winner = room["players"][winner_index]
            room_state_msg["game_ended"] = {
                "winner": winner,
                "total_sum": total_sum,
                "can_restart": True
            }
    
    await websocket.send_json(room_state_msg)
    
    try:
        while True:
            data = await websocket.receive_json()
            await handle_websocket_message(room_code, username, data)
    except WebSocketDisconnect:
        # Handle disconnect
        if room_code in active_connections and username in active_connections[room_code]:
            del active_connections[room_code][username]


async def handle_websocket_message(room_code: str, username: str, data: dict):
    room = rooms.get(room_code)
    if not room:
        return
    
    message_type = data.get("type")
    
    if message_type == "start_game":
        if username != room["creator"]:
            return
        
        if room["game_started"]:
            return
        
        if len(room["players"]) < MIN_PLAYERS:
            await active_connections[room_code][username].send_json({
                "type": "error",
                "message": f"Need at least {MIN_PLAYERS} players to start"
            })
            return
        
        # Initialize game
        room["game_started"] = True
        room["game_state"] = {
            "current_turn": 0,
            "current_player_index": 0,
            "choices": generate_choices(),
            "turn_start_time": datetime.utcnow().isoformat(),
            "player_choices": [],
            "turn_timer_task": None
        }
        
        # Start turn timer and store task reference
        room["game_state"]["turn_timer_task"] = asyncio.create_task(run_turn_timer(room_code, 0))
        
        await broadcast_to_room(room_code, {
            "type": "game_started",
            "players": room["players"],
            "current_player": room["players"][0],
            "choices": room["game_state"]["choices"],
            "turn": 1,
            "max_turns": MAX_TURNS,
            "turn_time": TURN_TIME_SECONDS
        })
    
    elif message_type == "make_choice":
        if not room["game_started"]:
            return
        
        game_state = room["game_state"]
        current_player = room["players"][game_state["current_player_index"]]
        
        if username != current_player:
            return
        
        choice = data.get("choice")
        if choice not in game_state["choices"]:
            return
        
        # Cancel the current turn timer since player made a choice
        if game_state.get("turn_timer_task"):
            game_state["turn_timer_task"].cancel()
            game_state["turn_timer_task"] = None
        
        # Record choice
        game_state["player_choices"].append({
            "player": username,
            "choice": choice,
            "turn": game_state["current_turn"]
        })
        
        await advance_turn(room_code)
    
    elif message_type == "exit_game":
        await handle_player_exit(room_code, username)
    
    elif message_type == "restart_game":
        if username != room["creator"]:
            return
        
        # Allow restart if game has ended (game_state exists but game_started is False)
        if room.get("game_state") is not None:
            await restart_game(room_code)


async def run_turn_timer(room_code: str, turn_number: int):
    try:
        await asyncio.sleep(TURN_TIME_SECONDS)
    except asyncio.CancelledError:
        # Timer was cancelled, player made a choice
        return
    
    if room_code not in rooms:
        return
    
    room = rooms[room_code]
    if not room["game_started"]:
        return
    
    game_state = room["game_state"]
    
    # Verify this timer is still for the current turn
    if game_state["current_turn"] != turn_number:
        return
    
    current_player = room["players"][game_state["current_player_index"]]
    
    # Check if player made a choice
    current_turn_choices = [c for c in game_state["player_choices"] if c["turn"] == game_state["current_turn"]]
    
    if not current_turn_choices:
        # Make random choice for player
        random_choice = random.choice(game_state["choices"])
        game_state["player_choices"].append({
            "player": current_player,
            "choice": random_choice,
            "turn": game_state["current_turn"],
            "auto": True
        })
        
        await broadcast_to_room(room_code, {
            "type": "auto_choice",
            "player": current_player,
            "choice": random_choice
        })
        
        # Clear timer task reference before advancing
        game_state["turn_timer_task"] = None
        await advance_turn(room_code)


async def advance_turn(room_code: str):
    room = rooms[room_code]
    game_state = room["game_state"]
    
    game_state["current_turn"] += 1
    
    # Check if game is over
    if game_state["current_turn"] >= MAX_TURNS:
        # Cancel any pending timer
        if game_state.get("turn_timer_task"):
            game_state["turn_timer_task"].cancel()
            game_state["turn_timer_task"] = None
        await end_game(room_code)
        return
    
    # Move to next player
    game_state["current_player_index"] = (game_state["current_player_index"] + 1) % len(room["players"])
    game_state["choices"] = generate_choices()
    game_state["turn_start_time"] = datetime.utcnow().isoformat()
    
    current_player = room["players"][game_state["current_player_index"]]
    
    # Start new turn timer and store task reference
    game_state["turn_timer_task"] = asyncio.create_task(run_turn_timer(room_code, game_state["current_turn"]))
    
    await broadcast_to_room(room_code, {
        "type": "next_turn",
        "current_player": current_player,
        "choices": game_state["choices"],
        "turn": game_state["current_turn"] + 1,
        "max_turns": MAX_TURNS,
        "turn_time": TURN_TIME_SECONDS
    })


async def end_game(room_code: str):
    room = rooms[room_code]
    game_state = room["game_state"]
    
    # Calculate total sum
    total_sum = sum(choice["choice"] for choice in game_state["player_choices"])
    winner_index = abs(total_sum) % len(room["players"])
    winner = room["players"][winner_index]
    
    room["game_started"] = False
    
    await broadcast_to_room(room_code, {
        "type": "game_ended",
        "winner": winner,
        "total_sum": total_sum,
        "choices": game_state["player_choices"],
        "can_restart": True
    })


async def restart_game(room_code: str):
    room = rooms[room_code]
    
    room["game_started"] = True
    room["game_state"] = {
        "current_turn": 0,
        "current_player_index": 0,
        "choices": generate_choices(),
        "turn_start_time": datetime.utcnow().isoformat(),
        "player_choices": [],
        "turn_timer_task": None
    }
    
    # Start turn timer and store task reference
    room["game_state"]["turn_timer_task"] = asyncio.create_task(run_turn_timer(room_code, 0))
    
    await broadcast_to_room(room_code, {
        "type": "game_started",
        "players": room["players"],
        "current_player": room["players"][0],
        "choices": room["game_state"]["choices"],
        "turn": 1,
        "max_turns": MAX_TURNS,
        "turn_time": TURN_TIME_SECONDS
    })


async def handle_player_exit(room_code: str, username: str):
    if room_code not in rooms:
        return
    
    room = rooms[room_code]
    
    if username not in room["players"]:
        return
    
    room["players"].remove(username)
    
    # Remove from connections
    if room_code in active_connections and username in active_connections[room_code]:
        del active_connections[room_code][username]
    
    # Check if room is empty or game cannot continue
    if len(room["players"]) == 0:
        # Delete room
        del rooms[room_code]
        if room_code in active_connections:
            del active_connections[room_code]
        return
    
    # If game is running and not enough players
    if room["game_started"] and len(room["players"]) < MIN_PLAYERS:
        room["game_started"] = False
        await broadcast_to_room(room_code, {
            "type": "game_ended",
            "reason": "Not enough players",
            "can_restart": False
        })
    
    # If creator left, assign new creator
    if username == room["creator"] and room["players"]:
        room["creator"] = room["players"][0]
    
    await broadcast_to_room(room_code, {
        "type": "player_left",
        "username": username,
        "players": room["players"],
        "creator": room["creator"]
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
