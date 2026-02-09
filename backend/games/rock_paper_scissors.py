"""
Rock Paper Scissors Game (Example)
A game where players choose rock, paper, or scissors.
Winner is determined by who wins the most rounds.
"""

import random
from datetime import datetime
from typing import Any, Dict, List
from game_engine import GameEngine, GameConfig, GameState, GameStatus, PlayerState, PlayerStatus, TurnState


class RockPaperScissorsGame(GameEngine):
    """
    Rock Paper Scissors Game Implementation
    
    Rules:
    - Each turn, a random player plays against another random player
    - Best of N rounds determines winner
    - Scoring: Win = 1 point, Draw = 0.5 point, Loss = 0 points
    """
    
    CHOICES = ["rock", "paper", "scissors"]
    
    async def initialize_game(self, players: List[str], game_id: str) -> GameState:
        """Initialize a new rock paper scissors game"""
        self.game_state = GameState(
            game_id=game_id,
            game_type="rock_paper_scissors",
            status=GameStatus.PLAYING,
            players=[PlayerState(username=p) for p in players],
            game_data={
                "rounds": [],
                "scores": {p: 0 for p in players},
                "matchups": []
            }
        )
        
        # Initialize first turn with random matchup
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
        
        current_player = self.game_state.players[self.game_state.current_turn.current_player_index]
        
        return {
            "type": "rps_turn",
            "current_player": current_player.username,
            "choices": self.CHOICES,
            "turn": self.game_state.current_turn.turn_number,
            "max_turns": self.config.max_rounds * len(self.game_state.players),
            "turn_time": self.config.turn_time,
            "scores": self.game_state.game_data["scores"]
        }
    
    async def process_turn_action(self, player: str, action: Any) -> bool:
        """Process a player's choice"""
        if not self.game_state:
            return False
        
        # Verify it's the correct player's turn
        current_player = self.game_state.players[self.game_state.current_turn.current_player_index]
        if current_player.username != player:
            return False
        
        # Verify action is valid choice
        if action not in self.CHOICES:
            return False
        
        # Store the action
        self.game_state.current_turn.player_action = action
        
        # Update history
        self.game_state.history.append({
            "turn": self.game_state.current_turn.turn_number,
            "player": player,
            "choice": action,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return True
    
    async def advance_turn(self) -> bool:
        """Move to next turn or complete round"""
        if not self.game_state:
            return False
        
        current_turn = self.game_state.current_turn.turn_number
        
        # Check if all players have played this round
        players_moved = current_turn + 1
        total_players = len(self.game_state.players)
        
        if players_moved % total_players == 0:
            # Complete the round
            await self._complete_round()
        
        self.game_state.current_turn.turn_number += 1
        
        # Check if game is over
        if self.game_state.current_turn.turn_number >= (self.config.max_rounds * len(self.game_state.players)):
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
    
    async def _complete_round(self):
        """Complete a round and calculate points"""
        # Get all choices from this round
        round_number = self.game_state.current_turn.turn_number // len(self.game_state.players)
        round_history = [
            h for h in self.game_state.history 
            if h["turn"] // len(self.game_state.players) == round_number
        ]
        
        # Determine winners
        if len(round_history) >= 2:
            choice1 = round_history[0]["choice"]
            choice2 = round_history[1]["choice"]
            player1 = round_history[0]["player"]
            player2 = round_history[1]["player"]
            
            winner = self._who_wins(choice1, choice2)
            
            if winner == 1:
                self.game_state.game_data["scores"][player1] += 1
            elif winner == 2:
                self.game_state.game_data["scores"][player2] += 1
            else:
                self.game_state.game_data["scores"][player1] += 0.5
                self.game_state.game_data["scores"][player2] += 0.5
    
    def _who_wins(self, choice1: str, choice2: str) -> int:
        """
        Determine winner between two choices
        Returns: 1 if choice1 wins, 2 if choice2 wins, 0 if draw
        """
        if choice1 == choice2:
            return 0
        
        if choice1 == "rock" and choice2 == "scissors":
            return 1
        if choice1 == "paper" and choice2 == "rock":
            return 1
        if choice1 == "scissors" and choice2 == "paper":
            return 1
        
        return 2
    
    async def handle_auto_play(self) -> str:
        """Generate automatic choice when player times out"""
        return random.choice(self.CHOICES)
    
    async def calculate_winner(self) -> str:
        """Calculate winner based on highest score"""
        if not self.game_state:
            return ""
        
        scores = self.game_state.game_data.get("scores", {})
        if not scores:
            return ""
        
        winner = max(scores.items(), key=lambda x: x[1])[0]
        return winner
    
    def get_game_status(self) -> Dict[str, Any]:
        """Get game status for broadcast"""
        if not self.game_state:
            return {}
        
        return {
            "game_type": "rock_paper_scissors",
            "status": self.game_state.status.value,
            "players": [
                {
                    "username": p.username,
                    "status": p.status.value,
                    "score": self.game_state.game_data["scores"].get(p.username, 0)
                }
                for p in self.game_state.players
            ],
            "round": self.game_state.current_turn.turn_number // len(self.game_state.players),
            "max_rounds": self.config.max_rounds,
            "winner": self.game_state.winner
        }
    
    def get_turn_status(self) -> Dict[str, Any]:
        """Get turn status for broadcast"""
        if not self.game_state:
            return {}
        
        current_player = self.game_state.players[self.game_state.current_turn.current_player_index]
        
        return {
            "current_player": current_player.username,
            "choices": self.CHOICES,
            "turn": self.game_state.current_turn.turn_number + 1,
            "max_turns": self.config.max_rounds * len(self.game_state.players),
            "turn_time": self.config.turn_time,
            "scores": self.game_state.game_data["scores"],
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
