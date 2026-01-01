"""
Move generator for a-math game.
Generates all valid moves from the current rack.
"""

from typing import List, Tuple, Optional
from itertools import combinations, permutations, product
from validation import validate_play, BLANK_VALUES, NUMBER_TILES
from tqdm import tqdm

# Tile type constants
SINGLE_DIGITS = {str(i) for i in range(10)}  # 0-9
MULTI_DIGIT_TILES = {str(i) for i in range(10, 21)}  # 10-20
OPERATORS = {'+', '-', '×', '÷', '×/÷', '+/-'}
COMPOUND_TILES = {'×/÷', '+/-'}  # Tiles that can be either of 2 values



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


def generate_equation_patterns(num_tiles: int) -> List[List[str]]:
    """
    Generate equation patterns following the format:
    [optional -] numbers operator numbers ... operator numbers = [optional -] numbers operator ... numbers
    
    Returns list of patterns, where each pattern is a list of slot types:
    - 'num': number slot (can be single digit or multi-digit, but multi-digit can't be adjacent to numbers)
    - 'op': operator slot
    - '=': equals sign
    - '-start': optional minus at start
    - '-after=': optional minus after equals
    """
    patterns = []
    
    # Must have at least one = sign
    # Minimum pattern: num op num = num (4 tiles)
    if num_tiles < 4:
        return []
    
    # Try different equation structures: [optional -] left_side = [optional -] right_side
    for left_len in range(1, num_tiles - 2):  # Need at least 1 for left, 1 for =, 1 for right
        right_len = num_tiles - left_len - 1  # -1 for =
        
        # Try with/without minus at start
        for has_minus_start in [False, True]:
            if has_minus_start and left_len < 2:
                continue  # Need at least 1 number after minus
            
            # Try with/without minus after equals
            for has_minus_after_eq in [False, True]:
                if has_minus_after_eq and right_len < 2:
                    continue  # Need at least 1 number after minus
                
                # Generate left side patterns
                left_patterns = generate_side_pattern(left_len - (1 if has_minus_start else 0))
                right_patterns = generate_side_pattern(right_len - (1 if has_minus_after_eq else 0))
                
                for left_pat in left_patterns:
                    for right_pat in right_patterns:
                        pattern = []
                        if has_minus_start:
                            pattern.append('-start')
                        pattern.extend(left_pat)
                        pattern.append('=')
                        if has_minus_after_eq:
                            pattern.append('-after=')
                        pattern.extend(right_pat)
                        
                        if len(pattern) == num_tiles:
                            patterns.append(pattern)
    
    return patterns


def generate_side_pattern(length: int) -> List[List[str]]:
    """
    Generate patterns for one side of equation (left or right).
    Format: numbers operator numbers ... operator numbers
    Must start and end with numbers, operators in between.
    """
    if length == 0:
        return [[]]
    if length == 1:
        return [['num']]  # Just a number
    
    patterns = []
    # Try different numbers of operators
    # For length n, can have 0 to (n-1)//2 operators (need at least 1 number between ops)
    max_ops = (length - 1) // 2
    
    for num_ops in range(max_ops + 1):
        # Pattern: num [op num] ... [op num]
        # Total: 1 + num_ops*2 = 1 + 2*num_ops
        if 1 + 2 * num_ops > length:
            continue
        
        # Remaining positions for additional numbers (can form multi-digit)
        remaining = length - (1 + 2 * num_ops)
        
        # Distribute remaining positions among number groups
        # Each number group can have 1-3 digits (max 3 digits per number)
        if remaining == 0:
            # Exact: num op num op num ...
            pattern = ['num']
            for _ in range(num_ops):
                pattern.extend(['op', 'num'])
            patterns.append(pattern)
        else:
            # Have extra positions - can add digits to numbers
            # Try distributing remaining digits among number groups
            for dist in distribute_digits(remaining, num_ops + 1, max_per_number=2):
                pattern = []
                for i, extra_digits in enumerate(dist):
                    if i == 0:
                        pattern.append('num')
                        pattern.extend(['num'] * extra_digits)
                    else:
                        pattern.append('op')
                        pattern.append('num')
                        pattern.extend(['num'] * extra_digits)
                if len(pattern) == length:
                    patterns.append(pattern)
    
    return patterns if patterns else [['num'] * length]  # Fallback: all numbers


def distribute_digits(total: int, num_groups: int, max_per_number: int = 2) -> List[List[int]]:
    """Distribute total digits among num_groups, with max_per_number per group"""
    if num_groups == 1:
        if total <= max_per_number:
            return [[total]]
        return []
    
    distributions = []
    for first in range(min(total + 1, max_per_number + 1)):
        for rest in distribute_digits(total - first, num_groups - 1, max_per_number):
            distributions.append([first] + rest)
    
    return distributions


def fill_pattern_with_tiles(pattern: List[str], available_tiles: List[str]) -> List[List[str]]:
    """
    Fill a pattern with actual tiles from available_tiles.
    Handles compound tiles (×/÷, +/-) and blank tiles (?).
    Returns list of possible tile sequences.
    """
    # Count what we need
    need_nums = pattern.count('num')
    need_ops = pattern.count('op')
    need_equals = pattern.count('=')
    need_minus_start = pattern.count('-start')
    need_minus_after_eq = pattern.count('-after=')
    
    # Get available tiles by type
    available_nums = [t for t in available_tiles if (t in SINGLE_DIGITS or t in MULTI_DIGIT_TILES or 
                                                      (t.startswith('?') and t[1:] in NUMBER_TILES))]
    available_ops = [t for t in available_tiles if (t in OPERATORS or 
                                                     (t.startswith('?') and t[1:] in OPERATORS))]
    available_equals = [t for t in available_tiles if (t == '=' or 
                                                        (t.startswith('?') and t[1:] == '='))]
    available_minus = [t for t in available_tiles if (t == '-' or 
                                                       (t.startswith('?') and t[1:] == '-'))]
    
    # Check if we have enough
    if len(available_nums) < need_nums:
        return []
    if len(available_ops) < need_ops:
        return []
    if len(available_equals) < need_equals:
        return []
    if len(available_minus) < need_minus_start + need_minus_after_eq:
        return []
    
    # Generate combinations
    sequences = []
    
    # Get combinations for each type
    num_combos = list(combinations(available_nums, need_nums))
    op_combos = list(combinations(available_ops, need_ops))
    eq_combos = list(combinations(available_equals, need_equals))
    minus_combos = list(combinations(available_minus, need_minus_start + need_minus_after_eq))
    
    for num_combo in num_combos:
        for op_combo in op_combos:
            for eq_combo in eq_combos:
                for minus_combo in minus_combos:
                    # Build sequence following pattern
                    sequence = []
                    num_idx = 0
                    op_idx = 0
                    eq_idx = 0
                    minus_idx = 0
                    
                    for item in pattern:
                        if item == 'num':
                            sequence.append(num_combo[num_idx])
                            num_idx += 1
                        elif item == 'op':
                            sequence.append(op_combo[op_idx])
                            op_idx += 1
                        elif item == '=':
                            sequence.append(eq_combo[eq_idx])
                            eq_idx += 1
                        elif item == '-start':
                            sequence.append(minus_combo[minus_idx])
                            minus_idx += 1
                        elif item == '-after=':
                            sequence.append(minus_combo[minus_idx])
                            minus_idx += 1
                    
                    sequences.append(sequence)
    
    return sequences


def expand_compound_tiles(tile_sequence: List[str]) -> List[List[str]]:
    """
    Expand compound tiles (×/÷, +/-) to all possible values.
    Returns list of sequences with compounds expanded.
    """
    compound_indices = [i for i, t in enumerate(tile_sequence) if t in COMPOUND_TILES]
    
    if not compound_indices:
        return [tile_sequence]
    
    expanded_sequences = []
    compound_value_lists = []
    for idx in compound_indices:
        if tile_sequence[idx] == '×/÷':
            compound_value_lists.append(['×', '÷'])
        elif tile_sequence[idx] == '+/-':
            compound_value_lists.append(['+', '-'])
    
    for combo in product(*compound_value_lists):
        expanded = tile_sequence[:]
        for i, idx in enumerate(compound_indices):
            expanded[idx] = combo[i]
        expanded_sequences.append(expanded)
    
    return expanded_sequences


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
    max_moves = 100  # Limit total moves to return
    unique_move_keys = set()  # Track unique moves for early exit
    
    # Expand rack to handle blank tiles - try all blank values for single blank
    expanded_racks = expand_rack_with_blanks(rack, limit=100)
    
    # For turn 0, must cover center square (7, 7)
    if turn == 0:
        # Start with longest moves first (8 tiles down to 4, minimum for equation)
        for num_tiles in tqdm(range(min(len(rack), 8), 3, -1), desc="Tile count", leave=False):
            if len(unique_move_keys) >= max_moves:
                break
            
            # Generate equation patterns for this length
            patterns = generate_equation_patterns(num_tiles)
            
            for expanded_rack in tqdm(expanded_racks, desc=f"Blank combos ({num_tiles} tiles)", leave=False, disable=len(expanded_racks) <= 1):
                if len(unique_move_keys) >= max_moves:
                    break
                
                for pattern in tqdm(patterns, desc="Patterns", leave=False, disable=len(patterns) < 5):
                    if len(unique_move_keys) >= max_moves:
                        break
                    
                    # Fill pattern with tiles
                    tile_sequences = fill_pattern_with_tiles(pattern, expanded_rack)
                    
                    for tile_seq in tile_sequences:
                        if len(unique_move_keys) >= max_moves:
                            break
                        
                        # Expand compound tiles (×/÷, +/-)
                        expanded_seqs = expand_compound_tiles(tile_seq)
                        
                        for expanded_seq in expanded_seqs:
                            if len(unique_move_keys) >= max_moves:
                                break
                            
                            # Don't permute the entire sequence - the pattern already constrains the order
                            # Only try the sequence as-is first (pattern-based order is usually correct)
                            sequences_to_try = [expanded_seq]
                            
                            # For number formations, try limited strategic swaps (only adjacent number tiles)
                            # This is much faster than full permutation
                            if num_tiles <= 7:
                                # Try swapping adjacent number tiles to form different multi-digit numbers
                                for i in range(len(expanded_seq) - 1):
                                    if len(sequences_to_try) >= 10:  # Limit to 10 variations
                                        break
                                    # Check if both are numbers
                                    tile1 = expanded_seq[i]
                                    tile2 = expanded_seq[i+1]
                                    val1 = tile1[1:] if tile1.startswith('?') else tile1
                                    val2 = tile2[1:] if tile2.startswith('?') else tile2
                                    if val1 in NUMBER_TILES and val2 in NUMBER_TILES:
                                        # Swap them
                                        swapped = expanded_seq[:]
                                        swapped[i], swapped[i+1] = swapped[i+1], swapped[i]
                                        if swapped not in sequences_to_try:
                                            sequences_to_try.append(swapped)
                            
                            for tile_perm in sequences_to_try:
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
        
        # For turn > 0, we can also extend existing sequences, not just create new equations
        # Try pattern-based first (for full equations), then fallback to simpler approach
        # Start with longest moves first (8 tiles down to 1)
        for num_tiles in tqdm(range(min(len(rack), 8), 0, -1), desc="Tile count", leave=False):
            if len(unique_move_keys) >= max_moves:
                break
            
            # For 4+ tiles, try pattern-based (full equations)
            if num_tiles >= 4:
                # Generate equation patterns for this length
                patterns = generate_equation_patterns(num_tiles)
                
                for expanded_rack in tqdm(expanded_racks, desc=f"Blank combos ({num_tiles} tiles)", leave=False, disable=len(expanded_racks) <= 1):
                    if len(unique_move_keys) >= max_moves:
                        break
                    
                    for pattern in tqdm(patterns, desc="Patterns", leave=False, disable=len(patterns) < 5):
                        if len(unique_move_keys) >= max_moves:
                            break
                        
                        # Fill pattern with tiles
                        tile_sequences = fill_pattern_with_tiles(pattern, expanded_rack)
                        
                        for tile_seq in tile_sequences:
                            if len(unique_move_keys) >= max_moves:
                                break
                            
                            # Expand compound tiles (×/÷, +/-)
                            expanded_seqs = expand_compound_tiles(tile_seq)
                            
                            for expanded_seq in expanded_seqs:
                                if len(unique_move_keys) >= max_moves:
                                    break
                                
                                # Don't permute the entire sequence - the pattern already constrains the order
                                sequences_to_try = [expanded_seq]
                                
                                # For number formations, try limited strategic swaps
                                if num_tiles <= 7:
                                    for i in range(len(expanded_seq) - 1):
                                        if len(sequences_to_try) >= 10:
                                            break
                                        tile1 = expanded_seq[i]
                                        tile2 = expanded_seq[i+1]
                                        val1 = tile1[1:] if tile1.startswith('?') else tile1
                                        val2 = tile2[1:] if tile2.startswith('?') else tile2
                                        if val1 in NUMBER_TILES and val2 in NUMBER_TILES:
                                            swapped = expanded_seq[:]
                                            swapped[i], swapped[i+1] = swapped[i+1], swapped[i]
                                            if swapped not in sequences_to_try:
                                                sequences_to_try.append(swapped)
                                
                                for tile_perm in sequences_to_try:
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
            
            # Fallback: For shorter moves (1-3 tiles) or if pattern-based didn't find enough, try simple combinations
            # Only do this for very short moves to avoid explosion
            if len(unique_move_keys) < max_moves and num_tiles <= 3:
                for expanded_rack in expanded_racks[:5]:  # Limit blank combos for fallback
                    if len(unique_move_keys) >= max_moves:
                        break
                    # Try simple combinations (not pattern-based) for very short moves
                    # Limit combinations to avoid explosion
                    combo_count = 0
                    for tile_combo in combinations(expanded_rack, num_tiles):
                        if len(unique_move_keys) >= max_moves or combo_count >= 50:  # Limit combos
                            break
                        combo_count += 1
                        # Try the combination as-is (no permutation to avoid explosion)
                        for start_row, start_col in list(adjacent_positions)[:20]:  # Limit positions
                            if len(unique_move_keys) >= max_moves:
                                break
                            # Try horizontal
                            if start_col + len(tile_combo) <= 15:
                                move_result = try_move(
                                    board, list(tile_combo), start_row, start_col, True, turn, chars
                                )
                                if move_result:
                                    coord, move_str = move_result
                                    move_key = (coord, move_str)
                                    if move_key not in unique_move_keys:
                                        unique_move_keys.add(move_key)
                                        valid_moves.append((coord, move_str, num_tiles))
                            # Try vertical
                            if start_row + len(tile_combo) <= 15:
                                move_result = try_move(
                                    board, list(tile_combo), start_row, start_col, False, turn, chars
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
