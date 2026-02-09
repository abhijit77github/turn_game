"""
Game Registry and Configuration
"""

from typing import Dict, Any, List
from game_engine import GameManager, GameConfig
from games.number_picker import NumberPickerGame
from games.rock_paper_scissors import RockPaperScissorsGame
from games.chain_reaction import ChainReactionGame


# Initialize global game manager
game_manager = GameManager()


def initialize_games():
    """Register all available games"""
    game_manager.register_game("number_picker", NumberPickerGame)
    game_manager.register_game("rock_paper_scissors", RockPaperScissorsGame)
    game_manager.register_game("chain_reaction", ChainReactionGame)
    # Register more games here as they are created
    # game_manager.register_game("trivia", TriviaGame)


def get_game_config(game_type: str, custom_config: Dict[str, Any] = None) -> GameConfig:
    """Get game configuration with defaults"""
    
    default_configs = {
        "number_picker": GameConfig(
            game_type="number_picker",
            min_players=2,
            max_players=6,
            turn_time=10,
            max_rounds=5
        ),
        "rock_paper_scissors": GameConfig(
            game_type="rock_paper_scissors",
            min_players=2,
            max_players=2,
            turn_time=10,
            max_rounds=5
        ),
        "chain_reaction": GameConfig(
            game_type="chain_reaction",
            min_players=2,
            max_players=6,
            turn_time=15,  # Longer turns for strategy
            max_rounds=10  # More rounds for longer game
        ),
        # Add more game configs here
    }
    
    config = default_configs.get(game_type)
    if not config:
        raise ValueError(f"Unknown game type: {game_type}")
    
    # Override with custom config if provided
    if custom_config:
        for key, value in custom_config.items():
            if hasattr(config, key):
                setattr(config, key, value)
    
    return config


def get_available_games() -> List[Dict[str, Any]]:
    """Get list of all available games with info"""
    games = []
    for game_name in game_manager.list_available_games():
        game_info = game_manager.get_game_info(game_name)
        games.append(game_info)
    return games
