"""
Move generator for a-math game.
Generates all valid moves from the current rack.
"""

from typing import List, Tuple, Optional
from itertools import combinations, permutations, product
from validation import validate_play, BLANK_VALUES, NUMBER_TILES
from tqdm import tqdm



def format_coord(row: int, col: int, is_horizontal: bool) -> str:
    """Format coordinate as string (e.g., '8G' for vertical, 'G8' for horizontal)"""
    letter = chr(ord('A') + col)
    number = row + 1
    if is_horizontal:
        return f"{number}{letter}"
    else:
        return f"{letter}{number}"


def tile_to_identifier(tile: str) -> str:
    """
    Convert a tile key to an identifier string for commit command.
    - Blank tiles (stored as "?value") should use "(value)" format
    - Regular tiles use their key directly
    """
    if tile.startswith('?'):
        # Blank tile - use (value) format
        value = tile[1:]
        return f"({value})"
    return tile


def expand_rack_with_blanks(rack: List[str], limit: int = 10) -> List[List[str]]:
    """
    Expand rack to handle blank tiles.
    For each blank tile "?", generate possible values (limited to avoid explosion).
    Returns list of expanded racks (each with blank tiles replaced by "?value").
    """
    expanded_racks = []
    blank_indices = [i for i, tile in enumerate(rack) if tile == '?']
    
    if not blank_indices:
        # No blanks, return original rack
        return [rack]
    
    # Try all valid blank values (0-20, +, -, ×, ÷, =)
    # For single blank, try all values. For multiple blanks, limit combinations.
    all_blank_values = list(BLANK_VALUES)
    
    if len(blank_indices) == 1:
        # Single blank - try all possible values
        for blank_value in all_blank_values:
            expanded_rack = rack[:]
            expanded_rack[blank_indices[0]] = f"?{blank_value}"
            expanded_racks.append(expanded_rack)
    else:
        # Multiple blanks - limit combinations to avoid explosion
        # Prioritize common values: 0-9, operators, then higher numbers
        common_values = [str(i) for i in range(10)] + ['+', '-', '×', '÷', '=']
        less_common_values = [str(i) for i in range(10, 21)]
        
        # Try common values first, then mix in less common ones
        blank_value_lists = [common_values for _ in blank_indices]
        count = 0
        for blank_combo in product(*blank_value_lists):
            if count >= limit:
                break
            expanded_rack = rack[:]
            for idx, blank_idx in enumerate(blank_indices):
                expanded_rack[blank_idx] = f"?{blank_combo[idx]}"
            expanded_racks.append(expanded_rack)
            count += 1
    
    return expanded_racks


def format_move_tiles(positions_used: List[Tuple[int, int, Optional[str]]]) -> str:
    """
    Format move tiles as comma-separated string, using '.' for existing tiles.
    positions_used: List of (row, col, tile) tuples where tile is None for existing tiles
    Returns the formatted string.
    """
    result = []
    
    for r, c, tile in positions_used:
        if tile is None:
            # Existing tile - use '.'
            result.append('.')
        else:
            # New tile - convert to identifier
            identifier = tile_to_identifier(tile)
            result.append(identifier)
    
    return ','.join(result)


def try_move(
    board: List[List[str]],
    tiles: List[str],
    start_row: int,
    start_col: int,
    is_horizontal: bool,
    turn: int,
    chars: dict
) -> Optional[Tuple[str, str]]:
    """
    Try to place tiles at the given position and orientation.
    Returns (coordinate, move_string) if valid, None otherwise.
    """
    positions_used = []
    tile_idx = 0
    pos = 0
    
    # Build the sequence of positions, handling existing tiles
    while tile_idx < len(tiles):
        if is_horizontal:
            r, c = start_row, start_col + pos
        else:
            r, c = start_row + pos, start_col
        
        if r >= 15 or c >= 15:
            # Out of bounds before placing all tiles
            return None
        
        if board[r][c] != ' ':
            # Existing tile - skip it
            positions_used.append((r, c, None))
            pos += 1
        else:
            # Empty position - place a tile
            positions_used.append((r, c, tiles[tile_idx]))
            tile_idx += 1
            pos += 1
    
    # Collect new tiles for validation
    new_tiles = []
    for r, c, tile in positions_used:
        if tile is not None:
            new_tiles.append((r, c, tile))
    
    # Validate the play - validate_play now handles multi-digit adjacency check
    if new_tiles:
        # validate_play returns (is_valid, error_message, parsed_equations)
        is_valid, error_message, _ = validate_play(
            board, new_tiles, turn, chars, is_horizontal
        )
        if is_valid:
            # Format the move string
            move_str = format_move_tiles(positions_used)
            coord = format_coord(start_row, start_col, is_horizontal)
            return (coord, move_str)
    
    return None


def generate_moves(
    board: List[List[str]],
    rack: List[str],
    turn: int,
    chars: dict
) -> List[Tuple[str, str, int]]:
    """
    Generate all valid moves from the current rack.
    Prioritizes longer moves first, then generates up to 100 moves sorted by length.
    
    Returns:
        List of (coordinate, move_string, num_tiles) tuples, sorted by num_tiles (descending)
    """
    valid_moves = []
    max_moves = 10  # Limit total moves to return
    unique_move_keys = set()  # Track unique moves for early exit
    
    # Expand rack to handle blank tiles - try all blank values for single blank
    expanded_racks = expand_rack_with_blanks(rack, limit=10)  # Increase limit for better coverage
    
    # For turn 0, must cover center square (7, 7)
    if turn == 0:
        # Start with longest moves first (8 tiles down to 1)
        for num_tiles in tqdm(range(min(len(rack), 8), 0, -1), desc="Tile count", leave=False):
            if len(unique_move_keys) >= max_moves:
                break
            for expanded_rack in tqdm(expanded_racks, desc=f"Blank combos ({num_tiles} tiles)", leave=False, disable=len(expanded_racks) <= 1):
                if len(unique_move_keys) >= max_moves:
                    break
                tile_combos = list(combinations(expanded_rack, num_tiles))
                for tile_combo in tqdm(tile_combos, desc=f"Combinations", leave=False, disable=len(tile_combos) < 10):
                    if len(unique_move_keys) >= max_moves:
                        break
                    for tile_perm in set(permutations(tile_combo)):
                        if len(unique_move_keys) >= max_moves:
                            break
                        # Try placements that include center square
                        for offset in range(len(tile_perm)):
                            if len(unique_move_keys) >= max_moves:
                                break
                            # Try horizontal
                            start_col = 7 - offset
                            if start_col >= 0 and start_col + len(tile_perm) <= 15:
                                move_result = try_move(
                                    board, list(tile_perm), 7, start_col, True, turn, chars
                                )
                                if move_result:
                                    coord, move_str = move_result
                                    move_key = (coord, move_str)
                                    if move_key not in unique_move_keys:
                                        unique_move_keys.add(move_key)
                                        valid_moves.append((coord, move_str, num_tiles))
                            
                            # Try vertical
                            start_row = 7 - offset
                            if start_row >= 0 and start_row + len(tile_perm) <= 15:
                                move_result = try_move(
                                    board, list(tile_perm), start_row, 7, False, turn, chars
                                )
                                if move_result:
                                    coord, move_str = move_result
                                    move_key = (coord, move_str)
                                    if move_key not in unique_move_keys:
                                        unique_move_keys.add(move_key)
                                        valid_moves.append((coord, move_str, num_tiles))
    else:
        # For subsequent turns, must touch existing tiles
        # Find all positions adjacent to existing tiles
        adjacent_positions = set()
        for row in range(15):
            for col in range(15):
                if board[row][col] != ' ':
                    # Add adjacent positions
                    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nr, nc = row + dr, col + dc
                        if 0 <= nr < 15 and 0 <= nc < 15 and board[nr][nc] == ' ':
                            adjacent_positions.add((nr, nc))
        
        # Start with longest moves first (8 tiles down to 1)
        for num_tiles in tqdm(range(min(len(rack), 8), 0, -1), desc="Tile count", leave=False):
            if len(unique_move_keys) >= max_moves:
                break
            for expanded_rack in tqdm(expanded_racks, desc=f"Blank combos ({num_tiles} tiles)", leave=False, disable=len(expanded_racks) <= 1):
                if len(unique_move_keys) >= max_moves:
                    break
                tile_combos = list(combinations(expanded_rack, num_tiles))
                for tile_combo in tqdm(tile_combos, desc=f"Combinations", leave=False, disable=len(tile_combos) < 10):
                    if len(unique_move_keys) >= max_moves:
                        break
                    for tile_perm in set(permutations(tile_combo)):
                        if len(unique_move_keys) >= max_moves:
                            break
                        # Try each adjacent position as a starting point
                        for start_row, start_col in tqdm(adjacent_positions, desc="Positions", leave=False, disable=len(adjacent_positions) < 5):
                            if len(unique_move_keys) >= max_moves:
                                break
                            # Try horizontal
                            if start_col + len(tile_perm) <= 15:
                                move_result = try_move(
                                    board, list(tile_perm), start_row, start_col, True, turn, chars
                                )
                                if move_result:
                                    coord, move_str = move_result
                                    move_key = (coord, move_str)
                                    if move_key not in unique_move_keys:
                                        unique_move_keys.add(move_key)
                                        valid_moves.append((coord, move_str, num_tiles))
                            
                            # Try vertical
                            if start_row + len(tile_perm) <= 15:
                                move_result = try_move(
                                    board, list(tile_perm), start_row, start_col, False, turn, chars
                                )
                                if move_result:
                                    coord, move_str = move_result
                                    move_key = (coord, move_str)
                                    if move_key not in unique_move_keys:
                                        unique_move_keys.add(move_key)
                                        valid_moves.append((coord, move_str, num_tiles))
    
    # Moves are already deduplicated and collected in order (longest first)
    # Sort by number of tiles (descending), then by coordinate
    sorted_moves = sorted(valid_moves, key=lambda x: (-x[2], x[0], x[1]))
    
    # Limit to 100 moves
    return sorted_moves[:max_moves]
