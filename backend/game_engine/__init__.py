"""
Game Engine Core Module
Provides base classes and interfaces for implementing turn-based games
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import asyncio


class GameStatus(Enum):
    """Game state enumeration"""
    WAITING = "waiting"
    PLAYING = "playing"
    FINISHED = "finished"
    PAUSED = "paused"


class PlayerStatus(Enum):
    """Player state enumeration"""
    JOINED = "joined"
    READY = "ready"
    PLAYING = "playing"
    FINISHED = "finished"
    DISCONNECTED = "disconnected"


@dataclass
class GameConfig:
    """Configuration for a game"""
    game_type: str
    min_players: int = 2
    max_players: int = 6
    turn_time: int = 10  # seconds
    max_rounds: int = 5
    custom_config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PlayerState:
    """State of a player in a game"""
    username: str
    status: PlayerStatus = PlayerStatus.JOINED
    score: int = 0
    stats: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TurnState:
    """State of the current turn"""
    turn_number: int
    current_player_index: int
    start_time: str
    player_action: Optional[Any] = None
    auto_played: bool = False


@dataclass
class GameState:
    """Complete state of a game"""
    game_id: str
    game_type: str
    status: GameStatus = GameStatus.WAITING
    players: List[PlayerState] = field(default_factory=list)
    current_turn: TurnState = field(default_factory=lambda: TurnState(0, 0, ""))
    game_data: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict[str, Any]] = field(default_factory=list)
    winner: Optional[str] = None


class GameEngine(ABC):
    """
    Abstract base class for all turn-based games.
    Implement this class to create a new game type.
    """
    
    def __init__(self, config: GameConfig):
        self.config = config
        self.game_state: Optional[GameState] = None
    
    @abstractmethod
    async def initialize_game(self, players: List[str], game_id: str) -> GameState:
        """Initialize a new game with given players"""
        pass
    
    @abstractmethod
    async def get_turn_data(self) -> Dict[str, Any]:
        """Get data needed for the current turn (choices, prompts, etc.)"""
        pass
    
    @abstractmethod
    async def process_turn_action(self, player: str, action: Any) -> bool:
        """Process player's turn action. Return True if valid, False otherwise"""
        pass
    
    @abstractmethod
    async def advance_turn(self) -> bool:
        """
        Move to next turn. 
        Return True if game continues, False if game is over
        """
        pass
    
    @abstractmethod
    async def handle_auto_play(self) -> Any:
        """Generate automatic action when player times out"""
        pass
    
    @abstractmethod
    async def calculate_winner(self) -> str:
        """Calculate and return the winner's username"""
        pass
    
    @abstractmethod
    def get_game_status(self) -> Dict[str, Any]:
        """Get current game status for broadcast"""
        pass
    
    @abstractmethod
    def get_turn_status(self) -> Dict[str, Any]:
        """Get current turn status for broadcast"""
        pass
    
    @abstractmethod
    def can_start_game(self) -> bool:
        """Check if game can be started (min players met, etc.)"""
        pass
    
    async def handle_player_disconnect(self, player: str) -> None:
        """Handle player disconnection. Can be overridden for custom logic."""
        if self.game_state:
            for p in self.game_state.players:
                if p.username == player:
                    p.status = PlayerStatus.DISCONNECTED
                    break
    
    async def handle_player_reconnect(self, player: str) -> None:
        """Handle player reconnection. Can be overridden for custom logic."""
        if self.game_state:
            for p in self.game_state.players:
                if p.username == player:
                    p.status = PlayerStatus.PLAYING
                    break
    
    def validate_config(self) -> bool:
        """Validate game configuration. Override for custom validation."""
        return (
            self.config.min_players >= 1 and
            self.config.max_players <= 1000 and
            self.config.min_players <= self.config.max_players and
            self.config.turn_time > 0 and
            self.config.max_rounds > 0
        )


class GameManager:
    """
    Manages game instances and routing.
    Maintains registry of available game types.
    """
    
    def __init__(self):
        self.game_types: Dict[str, type] = {}
        self.active_games: Dict[str, GameEngine] = {}
    
    def register_game(self, game_name: str, game_class: type) -> None:
        """Register a new game type"""
        if not issubclass(game_class, GameEngine):
            raise ValueError(f"{game_class} must inherit from GameEngine")
        self.game_types[game_name] = game_class
    
    def get_game_class(self, game_name: str) -> Optional[type]:
        """Get game class by name"""
        return self.game_types.get(game_name)
    
    def list_available_games(self) -> List[str]:
        """List all registered game types"""
        return list(self.game_types.keys())
    
    def create_game_instance(self, game_name: str, config: GameConfig) -> Optional[GameEngine]:
        """Create a game instance"""
        game_class = self.get_game_class(game_name)
        if not game_class:
            return None
        
        instance = game_class(config)
        if not instance.validate_config():
            return None
        
        return instance
    
    def store_game(self, game_id: str, game: GameEngine) -> None:
        """Store active game instance"""
        self.active_games[game_id] = game
    
    def get_game(self, game_id: str) -> Optional[GameEngine]:
        """Get active game instance"""
        return self.active_games.get(game_id)
    
    def remove_game(self, game_id: str) -> None:
        """Remove game instance"""
        if game_id in self.active_games:
            del self.active_games[game_id]
    
    def get_game_info(self, game_name: str) -> Dict[str, Any]:
        """Get information about a game type"""
        game_class = self.get_game_class(game_name)
        if not game_class:
            return {}
        
        # Convert snake_case to Title Case for display
        display_name = " ".join(word.capitalize() for word in game_name.split("_"))
        
        return {
            "name": game_name,
            "display_name": display_name,
            "class": game_class.__name__,
            "description": game_class.__doc__ or "",
        }
