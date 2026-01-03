"""
Score calculator for a-math game.

Calculates scores based on:
- Tile values from chars.json
- Bonus squares from bonus.json (3P, 2P, 3L, 2L)
- Only new tiles get bonus multipliers; existing tiles count at face value
"""

import json
from typing import List, Tuple, Dict, Optional


def load_bonus_squares(bonus_file: str = "bonus.json") -> Dict[str, List[Tuple[int, int]]]:
    """
    Load bonus squares from bonus.json.
    
    Returns:
        Dictionary with keys '3P', '2P', '3L', '2L' mapping to lists of (row, col) tuples
    """
    with open(bonus_file, 'r') as f:
        bonus_data = json.load(f)
    
    # Convert lists to tuples for easier comparison
    result = {}
    for bonus_type, positions in bonus_data.items():
        result[bonus_type] = [(pos[0], pos[1]) for pos in positions]
    
    return result


def get_tile_value(tile: str, chars: Dict) -> int:
    """
    Get the base value of a tile from chars.json.
    
    Uses the actual tile on the board, not the resolved value.
    For compound tiles like +/- or ×/÷, uses their base value (1).
    For blank tiles, uses value 0.
    
    Args:
        tile: Tile key from board (e.g., "8", "+", "×/÷", "+/-", "?5", "+/-:-")
        chars: Character definitions from chars.json
    
    Returns:
        Base value of the tile (0 if not found)
    
    NOTE: Compound tiles use their base value, not the resolved value.
    NOTE: Blank tiles always have value 0.
    """
    # Handle blank tiles (format: "?value")
    if tile.startswith('?'):
        # Blank tiles have value 0, regardless of what value they represent
        return 0
    
    # Handle locked compound tiles (format: "symbol:resolved_value")
    # Use the base value of the compound tile itself, not the resolved value
    if ':' in tile:
        parts = tile.split(':', 1)
        if len(parts) == 2 and parts[0] in ['×/÷', '+/-']:
            # Use the base value of the compound tile (e.g., +/- has value 1)
            compound_tile = parts[0]
            if compound_tile in chars:
                return chars[compound_tile].get('value', 0)
            return 0
    
    # Regular tile (including compound tiles like +/- and ×/÷)
    if tile in chars:
        value = chars[tile].get('value', 0)
        return value
    
    return 0


def get_piece_multiplier(row: int, col: int, bonus: Dict[str, List[Tuple[int, int]]]) -> int:
    """
    Get the piece multiplier for a position (3P = 3, 2P = 2, otherwise 1).
    
    Args:
        row: Row index (0-14)
        col: Column index (0-14)
        bonus: Bonus squares dictionary
    
    Returns:
        Multiplier (1, 2, or 3)
    """
    pos = (row, col)
    if pos in bonus.get('3P', []):
        return 3
    if pos in bonus.get('2P', []):
        return 2
    return 1


def get_equation_multiplier(
    equation_tiles: List[Tuple[int, int, str, bool]],
    bonus: Dict[str, List[Tuple[int, int]]]
) -> int:
    """
    Get the equation multiplier based on whether any NEW tile is on a 3L or 2L square.
    
    NOTE: Only new tiles activate equation multipliers. If multiple new tiles are on
    equation multiplier squares, they multiply together (e.g., 3L and 2L = 6x).
    
    Args:
        equation_tiles: List of (row, col, tile, is_new) tuples
        bonus: Bonus squares dictionary
    
    Returns:
        Total equation multiplier (1, 2, 3, 4, 6, or 9)
    """
    multiplier = 1
    
    for row, col, tile, is_new in equation_tiles:
        if not is_new:
            continue  # Only new tiles activate equation multipliers
        
        pos = (row, col)
        if pos in bonus.get('3L', []):
            multiplier *= 3
        elif pos in bonus.get('2L', []):
            multiplier *= 2
    
    return multiplier


def calculate_score(
    equation_tiles: List[Tuple[int, int, str, bool]],
    chars: Dict,
    bonus: Optional[Dict[str, List[Tuple[int, int]]]] = None,
    bonus_file: str = "bonus.json"
) -> int:
    """
    Calculate the score for an equation.
    
    Args:
        equation_tiles: List of (row, col, tile, is_new) tuples
            - row, col: Position on board (0-14)
            - tile: Tile key (e.g., "8", "+", "×/÷", "?5")
            - is_new: True if tile was placed this turn, False if it already existed
        chars: Character definitions from chars.json
        bonus: Optional pre-loaded bonus squares dictionary (if None, loads from bonus_file)
        bonus_file: Path to bonus.json file
    
    Returns:
        Total score for the equation
    
    Example:
        # New tiles: 10 at (7,7) on 3P, = at (7,8), 10 at (7,9) on 3P
        # Existing tile: + at (7,6) (face value only)
        # Equation: +10=10
        # Calculation:
        #   + (existing): 2 (face value, no multiplier)
        #   10 (new on 3P): 3 * 3 = 9
        #   = (new): 1
        #   10 (new on 3P): 3 * 3 = 9
        #   Base sum: 2 + 9 + 1 + 9 = 21
        #   No equation multiplier (no new tiles on 3L/2L)
        #   Total: 21
        
        # Example with equation multiplier:
        # New tiles: 3 at (0,0) on 3L, + at (0,1), 3 at (0,2) on 3L, = at (0,3), 6 at (0,4)
        # Calculation:
        #   3 (new on 3L): 1 * 1 = 1 (no piece multiplier)
        #   + (new): 2
        #   3 (new on 3L): 1 * 1 = 1
        #   = (new): 1
        #   6 (new): 2
        #   Base sum: 1 + 2 + 1 + 1 + 2 = 7
        #   Equation multiplier: 3 * 3 = 9 (two 3L squares)
        #   Total: 7 * 9 = 63
    """
    if bonus is None:
        bonus = load_bonus_squares(bonus_file)
    
    # Calculate base score for each tile
    base_score = 0
    
    for row, col, tile, is_new in equation_tiles:
        # Get base value of tile
        tile_value = get_tile_value(tile, chars)
        
        # Apply piece multiplier only if tile is new
        if is_new:
            piece_mult = get_piece_multiplier(row, col, bonus)
            tile_score = tile_value * piece_mult
        else:
            # Existing tiles count at face value only
            tile_score = tile_value
        
        base_score += tile_score
    
    # Apply equation multiplier (only if new tiles are on 3L/2L squares)
    equation_mult = get_equation_multiplier(equation_tiles, bonus)
    
    total_score = base_score * equation_mult
    
    return total_score


def calculate_play_score(
    new_tiles: List[Tuple[int, int, str]],
    equation_tiles: List[Tuple[int, int, str]],
    chars: Dict,
    bonus: Optional[Dict[str, List[Tuple[int, int]]]] = None,
    bonus_file: str = "bonus.json"
) -> int:
    """
    Convenience function to calculate score for a play.
    
    This function automatically marks tiles as new or existing based on new_tiles.
    
    Args:
        new_tiles: List of (row, col, tile) tuples for newly placed tiles
        equation_tiles: List of (row, col, tile) tuples for ALL tiles in the equation
            (both new and existing)
        chars: Character definitions from chars.json
        bonus: Optional pre-loaded bonus squares dictionary
        bonus_file: Path to bonus.json file
    
    Returns:
        Total score for the play
    
    Example:
        new_tiles = [(7, 7, "10"), (7, 8, "="), (7, 9, "10")]
        equation_tiles = [(7, 6, "+"), (7, 7, "10"), (7, 8, "="), (7, 9, "10")]
        # The + at (7,6) is existing, others are new
    """
    # Create a set of new tile positions for quick lookup
    new_positions = {(r, c) for r, c, _ in new_tiles}
    
    # Mark each tile as new or existing
    marked_tiles = []
    for row, col, tile in equation_tiles:
        is_new = (row, col) in new_positions
        marked_tiles.append((row, col, tile, is_new))
    
    return calculate_score(marked_tiles, chars, bonus, bonus_file)

