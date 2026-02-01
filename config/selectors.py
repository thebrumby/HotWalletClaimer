"""
Selectors configuration for game scripts.

This module provides centralized XPath selectors for all game UI elements.
When Telegram updates their UI, update these files instead of game scripts.
"""

import json
from pathlib import Path
from typing import Dict, Any


SELECTORS_DIR = Path(__file__).parent.parent / "selectors"


def load_selectors(game_name: str) -> Dict[str, Any]:
    """
    Load selectors configuration for a specific game.

    Args:
        game_name: Name of the game (e.g., 'xnode', 'hot', 'iceberg')

    Returns:
        Dictionary containing game selectors

    Raises:
        FileNotFoundError: If selectors file doesn't exist
        json.JSONDecodeError: If selectors file is invalid JSON

    Example:
        >>> selectors = load_selectors('xnode')
        >>> xpath = selectors['selectors']['skip_button']
    """
    path = SELECTORS_DIR / f"{game_name}.json"
    
    if not path.exists():
        raise FileNotFoundError(
            f"Selectors not found for '{game_name}'. "
            f"Expected file: {path}"
        )
    
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_selectors(game_name: str, selectors: Dict[str, Any]) -> None:
    """
    Save selectors configuration for a specific game.

    Args:
        game_name: Name of the game
        selectors: Dictionary containing game selectors

    Example:
        >>> selectors = {'selectors': {'skip': '//button[.//text()[contains(.,'Skip')]]'}}
        >>> save_selectors('xnode', selectors)
    """
    path = SELECTORS_DIR / f"{game_name}.json"
    
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(selectors, f, indent=2, ensure_ascii=False)


def list_games() -> list:
    """
    List all available games with selectors.

    Returns:
        List of game names that have selector files
    """
    return [f.stem for f in SELECTORS_DIR.glob("*.json")]


__all__ = ['load_selectors', 'save_selectors', 'list_games']
