"""
Number Picker Game
A simple turn-based game where players select numbers and the winner is determined by modulo.
"""

import random
from datetime import datetime
from typing import Any, Dict, List
from game_engine import GameEngine, GameConfig, GameState, GameStatus, PlayerState, PlayerStatus, TurnState


class NumberPickerGame(GameEngine):
    """
    Number Picker Game Implementation
    
    Rules:
    - Each turn, player selects from 5 random numbers (-100 to +100)
    - After max_rounds turns, winner is determined by: abs(sum) % num_players
    """
    
    async def initialize_game(self, players: List[str], game_id: str) -> GameState:
        """Initialize a new number picker game"""
        self.game_state = GameState(
            game_id=game_id,
            game_type="number_picker",
            status=GameStatus.PLAYING,
            players=[PlayerState(username=p) for p in players],
            game_data={
                "choices": [],
                "player_selections": {},
                "total_sum": 0
            }
        )
        
        # Initialize first turn
        self.game_state.current_turn = TurnState(
            turn_number=0,
            current_player_index=0,
            start_time=datetime.utcnow().isoformat()
        )
        
        return self.game_state
    
    async def get_turn_data(self) -> Dict[str, Any]:
        """Get choices for current turn"""
        if not self.game_state:
            return {}
        
        # Generate 5 random numbers if not already generated for this turn
        current_turn_key = f"turn_{self.game_state.current_turn.turn_number}"
        
        if current_turn_key not in self.game_state.game_data["choices"]:
            choices = [random.randint(-100, 100) for _ in range(5)]
            self.game_state.game_data["choices"].append({
                "turn": self.game_state.current_turn.turn_number,
                "options": choices
            })
        else:
            choices = self.game_state.game_data["choices"][-1]["options"]
        
        current_player = self.game_state.players[self.game_state.current_turn.current_player_index]
        
        return {
            "type": "number_picker_turn",
            "current_player": current_player.username,
            "choices": choices,
            "turn": self.game_state.current_turn.turn_number,
            "max_turns": self.config.max_rounds,
            "turn_time": self.config.turn_time
        }
    
    async def process_turn_action(self, player: str, action: Any) -> bool:
        """Process a player's number selection"""
        if not self.game_state:
            print(f"Game state is None")
            return False
        
        # Verify it's the correct player's turn
        current_player = self.game_state.players[self.game_state.current_turn.current_player_index]
        if current_player.username != player:
            print(f"Wrong player: {player} vs {current_player.username}")
            return False
        
        # Verify action is a valid choice
        if not isinstance(action, int):
            print(f"Action is not int: {action} (type: {type(action)})")
            return False
        
        # Get current turn's choices
        current_turn_key = f"turn_{self.game_state.current_turn.turn_number}"
        latest_choices = self.game_state.game_data["choices"][-1]["options"] if self.game_state.game_data["choices"] else []
        print(f"Current player: {current_player.username}, Action: {action}, Available choices: {latest_choices}")
        
        if action not in latest_choices:
            print(f"Action {action} not in choices {latest_choices}")
            return False
        
        # Record the selection
        if "player_selections" not in self.game_state.game_data:
            self.game_state.game_data["player_selections"] = {}
        
        self.game_state.game_data["player_selections"][player] = action
        self.game_state.current_turn.player_action = action
        
        # Update history
        self.game_state.history.append({
            "turn": self.game_state.current_turn.turn_number,
            "player": player,
            "action": action,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return True
    
    async def advance_turn(self) -> bool:
        """Move to next turn. Return True if game continues, False if game over"""
        if not self.game_state:
            return False
        
        self.game_state.current_turn.turn_number += 1
        
        # Check if game is over
        if self.game_state.current_turn.turn_number >= self.config.max_rounds:
            self.game_state.status = GameStatus.FINISHED
            winner = await self.calculate_winner()
            self.game_state.winner = winner
            return False
        
        # Move to next player
        num_players = len(self.game_state.players)
        self.game_state.current_turn.current_player_index = (
            self.game_state.current_turn.current_player_index + 1
        ) % num_players
        
        # Reset for new turn
        self.game_state.current_turn.start_time = datetime.utcnow().isoformat()
        self.game_state.current_turn.player_action = None
        self.game_state.current_turn.auto_played = False
        
        return True
    
    async def handle_auto_play(self) -> Any:
        """Generate automatic selection when player times out"""
        if not self.game_state:
            return None
        
        # Get current turn's choices
        latest_choices = self.game_state.game_data["choices"][-1]["options"] if self.game_state.game_data["choices"] else []
        
        if not latest_choices:
            return None
        
        auto_choice = random.choice(latest_choices)
        self.game_state.current_turn.auto_played = True
        return auto_choice
    
    async def calculate_winner(self) -> str:
        """Calculate winner based on total sum modulo"""
        if not self.game_state:
            return ""
        
        total_sum = 0
        selections = self.game_state.game_data.get("player_selections", {})
        
        for player in self.game_state.players:
            selection = selections.get(player.username, 0)
            total_sum += selection
        
        self.game_state.game_data["total_sum"] = total_sum
        
        num_players = len(self.game_state.players)
        winner_index = abs(total_sum) % num_players
        winner = self.game_state.players[winner_index].username
        
        return winner
    
    def get_game_status(self) -> Dict[str, Any]:
        """Get game status for broadcast"""
        if not self.game_state:
            return {}
        
        return {
            "game_type": "number_picker",
            "status": self.game_state.status.value,
            "players": [
                {
                    "username": p.username,
                    "status": p.status.value,
                    "score": p.score
                }
                for p in self.game_state.players
            ],
            "current_turn": self.game_state.current_turn.turn_number,
            "max_turns": self.config.max_rounds,
            "winner": self.game_state.winner
        }
    
    def get_turn_status(self) -> Dict[str, Any]:
        """Get turn status for broadcast"""
        if not self.game_state:
            return {}
        
        current_player = self.game_state.players[self.game_state.current_turn.current_player_index]
        
        # Get current choices
        latest_choices = []
        if self.game_state.game_data["choices"]:
            latest_choices = self.game_state.game_data["choices"][-1]["options"]
        
        return {
            "current_player": current_player.username,
            "choices": latest_choices,
            "turn": self.game_state.current_turn.turn_number + 1,
            "max_turns": self.config.max_rounds,
            "turn_time": self.config.turn_time,
            "auto_played": self.game_state.current_turn.auto_played
        }
    
    def can_start_game(self) -> bool:
        """Check if game can be started"""
        if not self.game_state:
            return False
        
        num_players = len(self.game_state.players)
        return (
            num_players >= self.config.min_players and
            num_players <= self.config.max_players
        )
