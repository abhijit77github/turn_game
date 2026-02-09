"""
Chain Reaction Game - Physics-based turn-based puzzle game

Game Rules:
- 10x6 grid board
- Players take turns placing balls on the board
- Each cell can hold a maximum of adjacent_cells - 1 balls
- When a cell exceeds its capacity, it explodes and spreads to adjacent cells
- Winning condition: All balls on board are the same color
"""

from typing import Dict, List, Any
from datetime import datetime
from game_engine import GameEngine, GameStatus, PlayerStatus, GameState, PlayerState, TurnState, GameConfig
import asyncio

class ChainReactionGame(GameEngine):
    """Chain Reaction game implementation"""
    
    BOARD_WIDTH = 6
    BOARD_HEIGHT = 10
    COLORS = ["red", "blue", "green", "yellow", "purple", "orange"]
    
    def __init__(self, config: GameConfig):
        super().__init__(config)
        self.game_state = None
    
    async def initialize_game(self, players: List[str], game_id: str) -> GameState:
        """Initialize a new chain reaction game"""
        self.game_state = GameState(
            game_id=game_id,
            game_type="chain_reaction",
            status=GameStatus.PLAYING,
            players=[PlayerState(username=p) for p in players],
            game_data={
                "board": self._create_empty_board(),
                "player_colors": {players[i]: self.COLORS[i] for i in range(len(players))},
                "move_history": [],
                "round": 0,
                "explosions": []
            }
        )
        
        # Initialize first turn
        self.game_state.current_turn = TurnState(
            turn_number=0,
            current_player_index=0,
            start_time=datetime.utcnow().isoformat()
        )
        
        return self.game_state
    
    def _create_empty_board(self) -> List[List[Dict[str, Any]]]:
        """Create an empty game board"""
        board = []
        for y in range(self.BOARD_HEIGHT):
            row = []
            for x in range(self.BOARD_WIDTH):
                adjacent_count = len(self._get_adjacent_cells_static(x, y))
                row.append({
                    "balls": [],  # List of colors
                    "x": x,
                    "y": y,
                    "critical_mass": adjacent_count  # Stability limit (capacity + 1)
                })
            board.append(row)
        return board
    
    def _get_adjacent_cells_static(self, x: int, y: int) -> List[tuple]:
        """Get adjacent cells without needing board (for init)"""
        adjacent = []
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.BOARD_WIDTH and 0 <= ny < self.BOARD_HEIGHT:
                adjacent.append((nx, ny))
        return adjacent
    
    def _get_adjacent_cells(self, x: int, y: int) -> List[tuple]:
        """Get adjacent cells (up, down, left, right)"""
        adjacent = []
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.BOARD_WIDTH and 0 <= ny < self.BOARD_HEIGHT:
                adjacent.append((nx, ny))
        return adjacent
    
    def _get_cell_stability_limit(self, x: int, y: int) -> int:
        """Get max balls a cell can hold before exploding"""
        adjacent_count = len(self._get_adjacent_cells(x, y))
        return adjacent_count  # Cell is unstable when it reaches this count
    
    async def get_turn_data(self) -> Dict[str, Any]:
        """Get current game state"""
        if not self.game_state:
            return {}
        
        current_player = self.game_state.players[self.game_state.current_turn.current_player_index]
        
        return {
            "current_player": current_player.username,
            "board": self.game_state.game_data["board"],
            "player_colors": self.game_state.game_data["player_colors"],
            "explosions": self.game_state.game_data.get("explosions", []),
            "turn": self.game_state.current_turn.turn_number,
            "round": self.game_state.game_data["round"],
            "max_turns": self.config.max_rounds * len(self.game_state.players),
            "turn_time": self.config.turn_time
        }
    
    async def process_turn_action(self, player: str, action: Any) -> Dict[str, Any]:
        """Process a player's move (x, y coordinates)
        
        Returns a dict with:
        - success: bool
        - events: list of game events to stream to frontend
          Each event is: {"type": "add_ball"|"explosion"|"spread", ...data...}
        """
        if not self.game_state:
            return {"success": False, "events": []}
        
        # Verify it's the correct player's turn
        current_player = self.game_state.players[self.game_state.current_turn.current_player_index]
        if current_player.username != player:
            return {"success": False, "events": []}
        
        # Parse action as [x, y]
        if not isinstance(action, (list, tuple)) or len(action) != 2:
            return {"success": False, "events": []}
        
        try:
            x, y = int(action[0]), int(action[1])
        except (ValueError, TypeError):
            return {"success": False, "events": []}
        
        # Validate coordinates
        if not (0 <= x < self.BOARD_WIDTH and 0 <= y < self.BOARD_HEIGHT):
            return {"success": False, "events": []}
        
        cell = self.game_state.game_data["board"][y][x]
        player_color = self.game_state.game_data["player_colors"][player]
        
        # If cell has balls of different color, cannot place
        if cell["balls"] and len(cell["balls"]) > 0 and cell["balls"][0] != player_color:
            return {"success": False, "events": []}
        
        # Place the ball
        cell["balls"].append(player_color)
        cell["balls"] = [player_color] * len(cell["balls"])
        
        # Record move
        self.game_state.game_data["move_history"].append({
            "player": player,
            "x": x,
            "y": y,
            "turn": self.game_state.current_turn.turn_number
        })
        
        # Create events list
        events = []
        
        # First event: ball added to cell
        events.append({
            "type": "add_ball",
            "x": x,
            "y": y,
            "color": player_color,
            "ball_count": len(cell["balls"])
        })
        
        # Check if critical mass reached
        if len(cell["balls"]) >= cell["critical_mass"]:
            # Generate explosion events via BFS
            explosion_events = await self._generate_explosion_events(x, y)
            events.extend(explosion_events)
            
            # Check win condition after explosions
            if self.game_state.game_data["round"] >= 1 and self._check_win_condition():
                self.game_state.status = GameStatus.FINISHED
                self.game_state.winner = self._determine_winner()
                events.append({
                    "type": "game_over",
                    "winner": self.game_state.winner
                })
        
        return {"success": True, "events": events}
    
    async def _generate_explosion_events(self, start_x: int, start_y: int) -> List[Dict]:
        """Generate explosion events using BFS queue
        
        Returns list of events in order with timing information
        """
        board = self.game_state.game_data["board"]
        queue = [(start_x, start_y)]
        events = []
        event_time = 0  # Track cumulative time for animation timing
        
        while queue:
            # Process all cells at current level (breadth-first)
            current_batch = []
            next_queue = []
            
            # Collect all cells that need to explode at this level
            while queue:
                x, y = queue.pop(0)
                cell = board[y][x]
                
                if len(cell["balls"]) >= cell["critical_mass"]:
                    current_batch.append((x, y))
            
            # Process each explosion individually with staggered timing
            cell_delay = 0
            for x, y in current_batch:
                cell = board[y][x]
                ball_color = cell["balls"][0] if cell["balls"] else None
                
                # Event: explosion (staggered by 0.5s per cell)
                explosion_time = event_time + cell_delay
                events.append({
                    "type": "explosion",
                    "x": x,
                    "y": y,
                    "color": ball_color,
                    "ball_count": len(cell["balls"]),
                    "time": explosion_time
                })
                
                # Clear the cell
                cell["balls"] = []
                
                # Spread to adjacent cells (start after explosion begins)
                for adj_x, adj_y in self._get_adjacent_cells(x, y):
                    adj_cell = board[adj_y][adj_x]
                    prev_count = len(adj_cell["balls"])
                    
                    # Add one ball and convert all to spreading color
                    adj_cell["balls"] = [ball_color] * (prev_count + 1)
                    
                    # Event: spread (after explosion starts)
                    events.append({
                        "type": "spread",
                        "from_x": x,
                        "from_y": y,
                        "to_x": adj_x,
                        "to_y": adj_y,
                        "color": ball_color,
                        "time": explosion_time + 0.5  # Start after explosion begins
                    })
                    
                    # Queue neighbor if it now exceeds critical mass
                    if len(adj_cell["balls"]) >= adj_cell["critical_mass"]:
                        next_queue.append((adj_x, adj_y))
                
                cell_delay += 0.5  # Stagger each cell by 0.5s for better visibility
            
            # Move to next level
            queue = next_queue
            event_time += (len(current_batch) * 0.5 + 1.5)  # Total time for this batch
        
        return events
    
    async def advance_turn(self) -> bool:
        """Move to next turn, return False if game ended"""
        # Check if game already ended (e.g., from explosion chain reaction)
        if self.game_state.status == GameStatus.FINISHED:
            print(f"[ADVANCE_TURN] Game already finished from previous explosion")
            return False
        
        # Move to next player
        current_player_index = self.game_state.current_turn.current_player_index
        next_player_index = (current_player_index + 1) % len(self.game_state.players)
        self.game_state.current_turn.current_player_index = next_player_index
        
        # Check if we've completed a full round
        # Round is complete when we wrap back to player 0
        completed_round = next_player_index == 0
        
        print(f"[ADVANCE_TURN] Players: {len(self.game_state.players)}, Current: {current_player_index} -> Next: {next_player_index}, Completed_round: {completed_round}, Current_round: {self.game_state.game_data['round']}")
        
        # Update round counter and check win condition
        if completed_round:
            self.game_state.game_data["round"] += 1
            print(f"[ROUND_COMPLETE] Round advanced to: {self.game_state.game_data['round']}")
            
            # Check win condition after completing a full round
            # Win condition: all balls on board are the same color
            print(f"[WIN_CHECK] Checking win condition at end of round {self.game_state.game_data['round']}")
            if self._check_win_condition():
                print(f"[GAME_OVER] All balls are same color! Winner: {self._determine_winner()}")
                self.game_state.status = GameStatus.FINISHED
                self.game_state.winner = self._determine_winner()
                return False
        
        self.game_state.current_turn.turn_number += 1
        self.game_state.current_turn.start_time = datetime.utcnow().isoformat()
        
        return True
    
    def _check_win_condition(self) -> bool:
        """Check if all balls are the same color"""
        board = self.game_state.game_data["board"]
        colors_found = set()
        total_balls = 0
        
        for row in board:
            for cell in row:
                for ball in cell["balls"]:
                    colors_found.add(ball)
                    total_balls += 1
        
        result = total_balls > 0 and len(colors_found) == 1
        if result:
            print(f"[WIN_CHECK] WIN! Round: {self.game_state.game_data['round']}, Total balls: {total_balls}, Color: {colors_found}")
        else:
            print(f"[WIN_CHECK] Not yet - Round: {self.game_state.game_data['round']}, Total balls: {total_balls}, Colors found: {colors_found}")
        
        # Win only if:
        # 1. There is at least one ball on the board
        # 2. All balls are the same color (only 1 color found)
        return result
    
    def _determine_winner(self) -> str:
        """Determine winner based on dominant color"""
        board = self.game_state.game_data["board"]
        color_count = {}
        
        for row in board:
            for cell in row:
                for ball in cell["balls"]:
                    color_count[ball] = color_count.get(ball, 0) + 1
        
        if not color_count:
            print("[WINNER] No balls on board, it's a draw")
            return "Draw"
        
        # Find player with dominant color
        dominant_color = max(color_count, key=color_count.get)
        print(f"[WINNER] Color count: {color_count}, Dominant color: {dominant_color}")
        
        for player, color in self.game_state.game_data["player_colors"].items():
            if color == dominant_color:
                print(f"[WINNER] Winner is {player} with {color_count[dominant_color]} balls")
                return player
        
        return "Draw"
    
    async def handle_auto_play(self) -> Any:
        """Auto-play: random valid move"""
        board = self.game_state.game_data["board"]
        current_player = self.game_state.players[self.game_state.current_turn.current_player_index]
        player_color = self.game_state.game_data["player_colors"][current_player.username]
        
        valid_moves = []
        for y in range(self.BOARD_HEIGHT):
            for x in range(self.BOARD_WIDTH):
                cell = board[y][x]
                # Can play on empty or own color
                if not cell["balls"] or cell["balls"][0] == player_color:
                    valid_moves.append([x, y])
        
        if not valid_moves:
            return [0, 0]  # Fallback
        
        import random
        return random.choice(valid_moves)
    
    def get_game_status(self) -> Dict[str, Any]:
        """Get game status"""
        return {
            "status": self.game_state.status.value if self.game_state else "unknown",
            "winner": self.game_state.winner if self.game_state else None,
            "round": self.game_state.game_data.get("round", 0) if self.game_state else 0
        }
    
    def get_turn_status(self) -> Dict[str, Any]:
        """Get current turn status"""
        if not self.game_state:
            return {}
        
        return {
            "turn_number": self.game_state.current_turn.turn_number,
            "current_player": self.game_state.players[self.game_state.current_turn.current_player_index].username
        }
    
    async def calculate_winner(self) -> str:
        """Calculate and return the winner's username"""
        return self.game_state.winner if self.game_state else "Unknown"
    
    def can_start_game(self) -> bool:
        """Check if game can be started (min players met)"""
        if not self.game_state:
            return False
        return len(self.game_state.players) >= self.config.min_players
