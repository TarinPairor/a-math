"""Tile-related utilities for resolving and displaying tiles."""

from typing import Optional, Dict


def get_tile_by_index(chars: Dict, index: int) -> Optional[str]:
    """Get tile key by index (0-25 for A-Z)"""
    for char_key, char_data in chars.items():
        if char_data.get('index') == index:
            return char_key
    return None


def resolve_tile(chars: Dict, identifier: str) -> Optional[str]:
    """
    Resolve a tile identifier to a tile key.
    identifier can be:
    - A numeric index (e.g., "0", "21")
    - An alias (e.g., "*", "/", "+/", "*/", "?")
    - A direct tile key (e.g., "×", "÷", "+/-")
    """
    identifier = identifier.strip()
    
    # Try as numeric index first
    try:
        index = int(identifier)
        tile = get_tile_by_index(chars, index)
        if tile:
            return tile
    except ValueError:
        pass
    
    # Try as alias
    for char_key, char_data in chars.items():
        if char_data.get('alias') == identifier:
            return char_key
    
    # Try as direct tile key
    if identifier in chars:
        return identifier
    
    return None


def get_tile_display(chars: Dict, char_key: str) -> str:
    """Get display string for a tile"""
    if char_key in chars:
        return chars[char_key]['ui']
    return char_key

