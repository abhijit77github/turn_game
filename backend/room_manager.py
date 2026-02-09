"""
Room Manager
Manages game rooms and player connections
"""

from typing import Dict, List, Optional
from datetime import datetime
from game_engine import GameManager, GameConfig
import uuid


class GameRoom:
    """Represents a game room"""
    
    def __init__(self, room_code: str, creator: str, game_type: str, game_engine):
        self.code = room_code
        self.creator = creator
        self.game_type = game_type
        self.game_engine = game_engine
        self.players: List[str] = [creator]
        self.created_at = datetime.utcnow().isoformat()
        self.game_started = False
        self.max_players = game_engine.config.max_players
    
    def add_player(self, username: str) -> bool:
        """Add player to room. Return False if room is full."""
        if len(self.players) >= self.max_players:
            return False
        if username in self.players:
            return False
        self.players.append(username)
        return True
    
    def remove_player(self, username: str) -> bool:
        """Remove player from room"""
        if username not in self.players:
            return False
        self.players.remove(username)
        return True
    
    def can_start(self) -> bool:
        """Check if game can be started"""
        return self.game_engine.can_start_game()
    
    def get_info(self) -> Dict:
        """Get room information"""
        return {
            "code": self.code,
            "creator": self.creator,
            "game_type": self.game_type,
            "players": self.players,
            "player_count": len(self.players),
            "max_players": self.max_players,
            "game_started": self.game_started,
            "created_at": self.created_at
        }


class RoomManager:
    """Manages all game rooms"""
    
    def __init__(self):
        self.rooms: Dict[str, GameRoom] = {}
    
    def create_room(self, creator: str, game_type: str, game_engine) -> Optional[GameRoom]:
        """Create a new game room"""
        room_code = self._generate_room_code()
        room = GameRoom(room_code, creator, game_type, game_engine)
        self.rooms[room_code] = room
        return room
    
    def get_room(self, room_code: str) -> Optional[GameRoom]:
        """Get room by code"""
        return self.rooms.get(room_code.upper())
    
    def join_room(self, room_code: str, username: str) -> bool:
        """Join a room"""
        room = self.get_room(room_code)
        if not room:
            return False
        return room.add_player(username)
    
    def leave_room(self, room_code: str, username: str) -> bool:
        """Leave a room"""
        room = self.get_room(room_code)
        if not room:
            return False
        
        removed = room.remove_player(username)
        
        # Delete empty rooms
        if len(room.players) == 0:
            del self.rooms[room_code]
        
        return removed
    
    def delete_room(self, room_code: str) -> bool:
        """Delete a room"""
        if room_code in self.rooms:
            del self.rooms[room_code]
            return True
        return False
    
    def list_rooms(self) -> List[Dict]:
        """List all rooms"""
        return [room.get_info() for room in self.rooms.values()]
    
    @staticmethod
    def _generate_room_code() -> str:
        """Generate a unique 6-character room code"""
        import random
        import string
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
