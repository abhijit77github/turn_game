"""
Game Template
Copy this file and implement your custom game logic.
"""

from typing import Any, Dict, List
from game_engine import GameEngine, GameConfig, GameState, GameStatus, PlayerState, TurnState
from datetime import datetime


class YourGameName(GameEngine):
    """
    Your Game Description
    
    Implement the abstract methods from GameEngine to create a new game type.
    """
    
    async def initialize_game(self, players: List[str], game_id: str) -> GameState:
        """Initialize a new game with given players"""
        # Create game state
        game_state = GameState(
            game_id=game_id,
            game_type="your_game_type",
            status=GameStatus.PLAYING,
            players=[PlayerState(username=p) for p in players],
            game_data={
                # Add your game-specific data here
            }
        )
        
        # Initialize first turn
        game_state.current_turn = TurnState(
            turn_number=0,
            current_player_index=0,
            start_time=datetime.utcnow().isoformat()
        )
        
        self.game_state = game_state
        return game_state
    
    async def get_turn_data(self) -> Dict[str, Any]:
        """Get data needed for the current turn"""
        # Return data that the frontend needs to render the turn
        return {
            "current_player": "player_username",
            "turn_number": 0,
            "turn_time": self.config.turn_time,
            # Add game-specific turn data
        }
    
    async def process_turn_action(self, player: str, action: Any) -> bool:
        """Process player's turn action. Return True if valid."""
        # Validate action and update game state
        # Record in history
        return True
    
    async def advance_turn(self) -> bool:
        """Move to next turn. Return False if game over."""
        # Update turn number
        # Check game end condition
        # Move to next player
        return True  # Game continues
    
    async def handle_auto_play(self) -> Any:
        """Generate automatic action when player times out"""
        return None  # Return appropriate auto-play action
    
    async def calculate_winner(self) -> str:
        """Calculate and return the winner's username"""
        return ""
    
    def get_game_status(self) -> Dict[str, Any]:
        """Get current game status for broadcast"""
        return {}
    
    def get_turn_status(self) -> Dict[str, Any]:
        """Get current turn status for broadcast"""
        return {}
    
    def can_start_game(self) -> bool:
        """Check if game can be started"""
        if not self.game_state:
            return False
        
        num_players = len(self.game_state.players)
        return (
            num_players >= self.config.min_players and
            num_players <= self.config.max_players
        )
