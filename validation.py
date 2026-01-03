"""
Play validation for a-math game.

This module validates plays according to the game rules:
- Starting player must cover center square
- Subsequent plays must touch existing tiles
- Equations must be valid mathematically
- Number formation rules
- Operator placement rules
- Calculation order rules
"""

from typing import List, Tuple, Optional, Set, Dict
import re
from itertools import product


# NOTE: Center square is at (7, 7) - row 8, column H (0-indexed: row 7, col 7)
CENTER_SQUARE = (7, 7)

# Valid number tiles (0-20)
NUMBER_TILES = {str(i) for i in range(21)}  # 0-20
OPERATOR_TILES = {'+', '-', '×', '÷', '×/÷', '+/-', '='}

# Valid values for blank tiles (0-20, +, -, ×, ÷, =)
BLANK_VALUES = {str(i) for i in range(21)} | {'+', '-', '×', '÷', '='}


def is_number_tile(tile: str) -> bool:
    """Check if tile is a number tile (0-20)"""
    return tile in NUMBER_TILES


def is_operator_tile(tile: str) -> bool:
    """Check if tile is an operator tile"""
    return tile in OPERATOR_TILES


def is_blank_tile(tile: str) -> bool:
    """Check if tile is a blank tile (stored as ?value)"""
    return tile.startswith('?')


def get_blank_value(tile: str) -> str:
    """Get the value a blank tile represents"""
    if is_blank_tile(tile):
        return tile[1:]
    return None


def validate_play(
    board: List[List[str]],
    new_tiles: List[Tuple[int, int, str]],  # (row, col, tile)
    turn: int,
    chars: Dict,
    is_horizontal: bool,  # True if play is horizontal, False if vertical
    debug: bool = False  # If True, return parsed equations for debugging
) -> Tuple[bool, Optional[str], Optional[List[Tuple[str, List[Tuple[int, int, str]]]]]]:
    """
    Validate a play according to all game rules.
    
    Args:
        board: Current board state (15x15)
        new_tiles: List of (row, col, tile) tuples for newly placed tiles
        turn: Current turn number (0-indexed)
        chars: Character definitions from chars.json
    
    Returns:
        (is_valid, error_message, parsed_equations) tuple
    """
    parsed_equations = []  # For debugging: list of (direction, sequence) tuples
    
    # NOTE: Starting player (turn 0) must cover center square
    if turn == 0:
        covers_center = any((r, c) == CENTER_SQUARE for r, c, _ in new_tiles)
        if not covers_center:
            return False, "First play must cover the center square (H8)", None
    
    # NOTE: Subsequent plays must touch at least one existing tile
    # NOTE: New tiles must not overlap with existing tiles
    if turn > 0:
        # Check that new tiles don't overlap with existing tiles
        for r, c, _ in new_tiles:
            if board[r][c] != ' ':
                return False, f"Cannot place tile at {chr(ord('A')+c)}{r+1}: position already occupied", None
        
        # Check that at least one new tile touches an existing tile
        # Use the original board (before new tiles are placed) to check for existing neighbors
        has_existing_neighbor = False
        for r, c, _ in new_tiles:
            # Check all 4 directions for existing tiles (not new tiles)
            neighbors = [(r-1, c), (r+1, c), (r, c-1), (r, c+1)]
            for nr, nc in neighbors:
                if 0 <= nr < 15 and 0 <= nc < 15:
                    # Check if this neighbor is an existing tile (not one of our new tiles)
                    is_new_tile = any(nr == new_r and nc == new_c for new_r, new_c, _ in new_tiles)
                    if not is_new_tile and board[nr][nc] != ' ':
                        has_existing_neighbor = True
                        break
            if has_existing_neighbor:
                break
        
        if not has_existing_neighbor:
            return False, "Play must touch at least one existing tile on the board", None
    
    # Extract all affected rows and columns
    affected_rows = set(r for r, _, _ in new_tiles)
    affected_cols = set(c for _, c, _ in new_tiles)
    
    # Create a temporary board with new tiles placed (for equation validation)
    temp_board = [row[:] for row in board]
    for r, c, tile in new_tiles:
        temp_board[r][c] = tile
    
    # NOTE: Validate ALL equations formed (horizontal and vertical) that include new tiles
    # NOTE: Check all rows and columns that have new tiles, extract full equation spans until empty spots
    # NOTE: ALL newly created equations must be valid
    new_positions = {(r, c) for r, c, _ in new_tiles}
    has_valid_equation = False
    
    # Check all horizontal equations that include new tiles
    checked_rows = set()
    for r, c, _ in new_tiles:
        if r not in checked_rows:
            checked_rows.add(r)
            # Extract contiguous sequences that include new tiles
            # Find all contiguous sequences in this row
            sequences_in_row = []
            current_sequence = []
            for c_seq in range(15):
                if temp_board[r][c_seq] != ' ':
                    tile = temp_board[r][c_seq]
                    # If it's a locked compound tile, use the locked value
                    resolved = _get_compound_resolved_value(tile)
                    if resolved:
                        current_sequence.append((r, c_seq, resolved))
                    else:
                        current_sequence.append((r, c_seq, tile))
                else:
                    if current_sequence:
                        # Check if this sequence includes any new tiles
                        if any((seq_r, seq_c) in new_positions for seq_r, seq_c, _ in current_sequence):
                            sequences_in_row.append(current_sequence)
                        current_sequence = []
            # Don't forget the last sequence if row doesn't end with empty
            if current_sequence:
                if any((seq_r, seq_c) in new_positions for seq_r, seq_c, _ in current_sequence):
                    sequences_in_row.append(current_sequence)
            
            # Validate each contiguous sequence that includes new tiles
            for sequence in sequences_in_row:
                
                # NOTE: For turn 0, single tiles in the play direction are not allowed - must form a valid equation
                # NOTE: Single tiles in the perpendicular direction are allowed
                if len(sequence) == 1:
                    if turn == 0 and is_horizontal:
                        return False, f"First play must form a valid equation with an equals sign. Single tiles are not allowed.", parsed_equations if debug else None
                    continue  # For turn > 0, or perpendicular direction, single tiles are allowed
                
                # NOTE: Validate perpendicular sequences if they have 2+ tiles
                # Single tiles in perpendicular direction are allowed (already handled above)
                # For vertical plays, horizontal sequences are in the perpendicular direction
                # For horizontal plays, vertical sequences are in the perpendicular direction
                if not is_horizontal:
                    # This is a horizontal sequence (perpendicular to vertical play)
                    # If it has 2+ tiles, validate it
                    if len(sequence) >= 2:
                        if debug:
                            # Resolve compound tiles and blank tiles for display using the temp_board
                            resolved_sequence = _resolve_sequence_for_display(sequence, temp_board)
                            parsed_equations.append(("perpendicular-horizontal", resolved_sequence))
                        has_equals = any(tile == '=' or (is_blank_tile(tile) and get_blank_value(tile) == '=') for _, _, tile in sequence)
                        if has_equals:
                            # It's an equation - must be valid
                            if debug:
                                is_valid, error, resolved_seq = validate_equation(sequence, chars, return_resolved=True)
                                if resolved_seq:
                                    # Update parsed equation with resolved sequence
                                    parsed_equations[-1] = ("perpendicular-horizontal", resolved_seq)
                            else:
                                is_valid, error = validate_equation(sequence, chars, return_resolved=False)
                            if not is_valid:
                                return False, f"Invalid perpendicular horizontal equation at row {r+1}: {error}", parsed_equations if debug else None
                        else:
                            # No equals sign - invalid for multi-tile perpendicular sequences
                            return False, f"Invalid perpendicular horizontal sequence at row {r+1}: sequence must contain an equals sign to form a valid equation", parsed_equations if debug else None
                    continue
                
                # This is a horizontal sequence in a horizontal play - validate it
                has_equals = any(tile == '=' or (is_blank_tile(tile) and get_blank_value(tile) == '=') for _, _, tile in sequence)
                if debug:
                    # Resolve compound tiles and blank tiles for display using the temp_board
                    resolved_sequence = _resolve_sequence_for_display(sequence, temp_board)
                    parsed_equations.append(("horizontal", resolved_sequence))
                if has_equals:
                    # It's an equation - must be valid (already checked len >= 2)
                    if debug:
                        is_valid, error, resolved_seq = validate_equation(sequence, chars, return_resolved=True)
                        if resolved_seq:
                            # Update parsed equation with resolved sequence
                            parsed_equations[-1] = ("horizontal", resolved_seq)
                    else:
                        is_valid, error = validate_equation(sequence, chars, return_resolved=False)
                    if not is_valid:
                        return False, f"Invalid horizontal equation at row {r+1}: {error}", parsed_equations if debug else None
                    has_valid_equation = True
                else:
                    # No equals sign - invalid if it has multiple tiles
                    if turn == 0:
                        return False, f"First play must form a valid equation with an equals sign. Sequences without equals signs are not allowed.", parsed_equations if debug else None
                    else:
                        return False, f"Invalid horizontal sequence at row {r+1}: sequence must contain an equals sign to form a valid equation", parsed_equations if debug else None
    
    # Check all vertical equations that include new tiles
    checked_cols = set()
    for r, c, _ in new_tiles:
        if c not in checked_cols:
            checked_cols.add(c)
            # Extract contiguous sequences that include new tiles
            # Find all contiguous sequences in this column
            sequences_in_col = []
            current_sequence = []
            for r_seq in range(15):
                if temp_board[r_seq][c] != ' ':
                    tile = temp_board[r_seq][c]
                    # If it's a locked compound tile, use the locked value
                    resolved = _get_compound_resolved_value(tile)
                    if resolved:
                        current_sequence.append((r_seq, c, resolved))
                    else:
                        current_sequence.append((r_seq, c, tile))
                else:
                    if current_sequence:
                        # Check if this sequence includes any new tiles
                        if any((seq_r, seq_c) in new_positions for seq_r, seq_c, _ in current_sequence):
                            sequences_in_col.append(current_sequence)
                        current_sequence = []
            # Don't forget the last sequence if column doesn't end with empty
            if current_sequence:
                if any((seq_r, seq_c) in new_positions for seq_r, seq_c, _ in current_sequence):
                    sequences_in_col.append(current_sequence)
            
            # Validate each contiguous sequence that includes new tiles
            for sequence in sequences_in_col:
                # NOTE: For turn 0, single tiles in the play direction are not allowed - must form a valid equation
                # NOTE: Single tiles in the perpendicular direction are allowed
                if len(sequence) == 1:
                    if turn == 0 and not is_horizontal:
                        return False, f"First play must form a valid equation with an equals sign. Single tiles are not allowed.", parsed_equations if debug else None
                    continue  # For turn > 0, or perpendicular direction, single tiles are allowed
                
                # NOTE: Validate perpendicular sequences if they have 2+ tiles
                # Single tiles in perpendicular direction are allowed (already handled above)
                # For horizontal plays, vertical sequences are in the perpendicular direction
                # For vertical plays, horizontal sequences are in the perpendicular direction
                if is_horizontal:
                    # This is a vertical sequence (perpendicular to horizontal play)
                    # If it has 2+ tiles, validate it
                    if len(sequence) >= 2:
                        if debug:
                            # Resolve compound tiles and blank tiles for display using the temp_board
                            resolved_sequence = _resolve_sequence_for_display(sequence, temp_board)
                            parsed_equations.append(("perpendicular-vertical", resolved_sequence))
                        has_equals = any(tile == '=' or (is_blank_tile(tile) and get_blank_value(tile) == '=') for _, _, tile in sequence)
                        if has_equals:
                            # It's an equation - must be valid
                            if debug:
                                is_valid, error, resolved_seq = validate_equation(sequence, chars, return_resolved=True)
                                if resolved_seq:
                                    # Update parsed equation with resolved sequence
                                    parsed_equations[-1] = ("perpendicular-vertical", resolved_seq)
                            else:
                                is_valid, error = validate_equation(sequence, chars, return_resolved=False)
                            if not is_valid:
                                return False, f"Invalid perpendicular vertical equation at column {chr(ord('A')+c)}: {error}", parsed_equations if debug else None
                        else:
                            # No equals sign - invalid for multi-tile perpendicular sequences
                            return False, f"Invalid perpendicular vertical sequence at column {chr(ord('A')+c)}: sequence must contain an equals sign to form a valid equation", parsed_equations if debug else None
                    continue
                
                # This is a vertical sequence in a vertical play - validate it
                has_equals = any(tile == '=' or (is_blank_tile(tile) and get_blank_value(tile) == '=') for _, _, tile in sequence)
                if debug:
                    # Resolve compound tiles and blank tiles for display using the temp_board
                    resolved_sequence = _resolve_sequence_for_display(sequence, temp_board)
                    parsed_equations.append(("vertical", resolved_sequence))
                if has_equals:
                    # It's an equation - must be valid (already checked len >= 2)
                    if debug:
                        is_valid, error, resolved_seq = validate_equation(sequence, chars, return_resolved=True)
                        if resolved_seq:
                            # Update parsed equation with resolved sequence
                            parsed_equations[-1] = ("vertical", resolved_seq)
                    else:
                        is_valid, error = validate_equation(sequence, chars, return_resolved=False)
                    if not is_valid:
                        return False, f"Invalid vertical equation at column {chr(ord('A')+c)}: {error}", parsed_equations if debug else None
                    has_valid_equation = True
                else:
                    # No equals sign - invalid if it has multiple tiles
                    if turn == 0:
                        return False, f"First play must form a valid equation with an equals sign. Sequences without equals signs are not allowed.", parsed_equations if debug else None
                    else:
                        return False, f"Invalid vertical sequence at column {chr(ord('A')+c)}: sequence must contain an equals sign to form a valid equation", parsed_equations if debug else None
    
    # For turn 0, ensure at least one valid equation was found
    if turn == 0 and not has_valid_equation:
        return False, f"First play must form a valid equation with an equals sign. Single tiles or sequences without equals signs are not allowed."
    
    # NOTE: Validate that multi-digit number tiles (10-20) are not adjacent to other number tiles
    # Check both: new multi-digit tiles adjacent to number tiles, and new number tiles adjacent to multi-digit tiles
    for r, c, tile in new_tiles:
        # Check if the new tile is a multi-digit tile adjacent to number tiles
        error = validate_multi_digit_adjacency(temp_board, r, c, tile, chars)
        if error:
            return False, error, parsed_equations if debug else None
        
        # Check if the new tile is a number tile adjacent to existing multi-digit tiles
        if is_number_tile(tile) or is_blank_tile(tile):
            # Get the actual value if it's a blank
            if is_blank_tile(tile):
                tile_value = get_blank_value(tile)
                if tile_value not in NUMBER_TILES:
                    continue  # Not a number blank, skip
            else:
                tile_value = tile
            
            # Only check if this is a single-digit number tile (not multi-digit)
            if tile_value in NUMBER_TILES and len(tile_value) == 1:
                # Check all 4 adjacent positions for existing multi-digit tiles
                neighbors = [(r-1, c), (r+1, c), (r, c-1), (r, c+1)]
                for nr, nc in neighbors:
                    if 0 <= nr < 15 and 0 <= nc < 15:
                        neighbor = temp_board[nr][nc]
                        if neighbor != ' ':
                            # Check if neighbor is a multi-digit tile (10-20)
                            if is_blank_tile(neighbor):
                                neighbor_value = get_blank_value(neighbor)
                                if neighbor_value not in NUMBER_TILES:
                                    continue
                            else:
                                neighbor_value = neighbor
                            
                            # Check if neighbor is a multi-digit number tile (10-20)
                            if neighbor_value in NUMBER_TILES and len(neighbor_value) > 1:
                                return False, f"Number tile '{tile_value}' cannot be placed adjacent to multi-digit number tile '{neighbor_value}'. Use single digits separated by commas (e.g., '1,7,2' instead of '2,17' or '17,2')", parsed_equations if debug else None
    
    # NOTE: Validate number formation rules
    for r, c, tile in new_tiles:
        if is_number_tile(tile) or is_blank_tile(tile):
            # Check if this forms a multi-digit number
            error = validate_number_formation(temp_board, r, c, chars)
            if error:
                return False, error, parsed_equations if debug else None
    
    # NOTE: Validate operator placement rules
    # NOTE: For compound tiles (+/-, ×/÷), they must be declared when placed
    # Extract all affected positions with operators or compound tiles
    operator_positions = []
    new_tile_positions = {(r, c) for r, c, _ in new_tiles}
    
    for r, c, tile in new_tiles:
        if is_operator_tile(tile) or is_blank_tile(tile) or tile in ['×/÷', '+/-']:
            operator_positions.append((r, c, tile))
            # Check if this is a new compound tile without a declared value
            if tile in ['×/÷', '+/-']:
                # New compound tile must have a declared value (stored as "symbol:resolved")
                # If it's just the symbol, that's an error
                if temp_board[r][c] == tile:
                    # The tile on the board is just the symbol, not declared
                    return False, f"Compound tile '{tile}' at {chr(ord('A')+c)}{r+1} must be declared with a value. Use format like '+/?+' or '23?21'", parsed_equations if debug else None
    
    # Validate all operator positions
    # For compound tiles, use the declared value from the board
    for r, c, tile in operator_positions:
        # Get the actual tile from the board (may have declared value)
        board_tile = temp_board[r][c]
        
        # Resolve the tile value
        if is_blank_tile(board_tile):
            resolved_tile = get_blank_value(board_tile)
            if resolved_tile not in ['+', '-', '×', '÷', '=']:
                continue  # Not an operator blank
        elif board_tile in ['×/÷', '+/-']:
            # Compound tile without declared value - should have been caught above
            return False, f"Compound tile '{board_tile}' at {chr(ord('A')+c)}{r+1} must be declared with a value", parsed_equations if debug else None
        else:
            # Check if it's a locked compound tile (format: "symbol:resolved")
            resolved = _get_compound_resolved_value(board_tile)
            if resolved:
                resolved_tile = resolved
            else:
                resolved_tile = board_tile
        
        if resolved_tile not in ['+', '-', '×', '÷', '=']:
            continue
        
        # Validate this operator, checking neighbors (including new tiles)
        error = validate_operator_placement_single_with_new_tiles(
            temp_board, r, c, resolved_tile, new_tile_positions, chars
        )
        
        if error:
            return False, error, parsed_equations if debug else None
    
    return True, None, parsed_equations if debug else None


def _get_compound_resolved_value(tile: str) -> Optional[str]:
    """
    Get the resolved value of a compound tile if it's locked in.
    Returns None if not a locked compound tile.
    Format: "symbol:resolved" (e.g., "+/-:+" or "×/÷:×")
    """
    if ':' in tile:
        parts = tile.split(':', 1)
        if len(parts) == 2 and parts[0] in ['×/÷', '+/-']:
            return parts[1]  # Return the resolved value
    return None


def extract_equation(
    board: List[List[str]],
    row: Optional[int],
    col: Optional[int],
    is_horizontal: bool
) -> Optional[List[Tuple[int, int, str]]]:
    """
    Extract a complete equation from a row or column.
    Returns list of (row, col, tile) tuples, or None if no equation found.
    For locked compound tiles, returns the locked value.
    """
    if is_horizontal:
        if row is None:
            return None
        tiles = []
        # Find the start of the equation (first non-empty tile)
        start_col = 0
        while start_col < 15 and board[row][start_col] == ' ':
            start_col += 1
        if start_col == 15:
            return None
        
        # Find the end of the equation
        end_col = 14
        while end_col >= 0 and board[row][end_col] == ' ':
            end_col -= 1
        
        # Extract all tiles in this range
        for c in range(start_col, end_col + 1):
            if board[row][c] != ' ':
                tile = board[row][c]
                # If it's a locked compound tile, use the resolved value
                resolved = _get_compound_resolved_value(tile)
                if resolved:
                    tiles.append((row, c, resolved))
                else:
                    tiles.append((row, c, tile))
        
        # Only return if there's an equals sign (it's an equation)
        if any(tile == '=' or (is_blank_tile(tile) and get_blank_value(tile) == '=') for _, _, tile in tiles):
            return tiles
    else:
        if col is None:
            return None
        tiles = []
        # Find the start of the equation
        start_row = 0
        while start_row < 15 and board[start_row][col] == ' ':
            start_row += 1
        if start_row == 15:
            return None
        
        # Find the end of the equation
        end_row = 14
        while end_row >= 0 and board[end_row][col] == ' ':
            end_row -= 1
        
        # Extract all tiles in this range
        for r in range(start_row, end_row + 1):
            if board[r][col] != ' ':
                tile = board[r][col]
                # If it's a locked compound tile, use the resolved value
                resolved = _get_compound_resolved_value(tile)
                if resolved:
                    tiles.append((r, col, resolved))
                else:
                    tiles.append((r, col, tile))
        
        # Only return if there's an equals sign
        if any(tile == '=' or (is_blank_tile(tile) and get_blank_value(tile) == '=') for _, _, tile in tiles):
            return tiles
    
    return None


def validate_equation(
    equation: List[Tuple[int, int, str]],
    chars: Dict,
    return_resolved: bool = False
) -> Tuple[bool, Optional[str], Optional[List[Tuple[int, int, str]]]]:
    """
    Validate that an equation is mathematically correct.
    Handles blank tiles and compound tiles (×/÷, +/-).
    
    Returns (is_valid, error_message, resolved_sequence)
    If return_resolved is True, returns the resolved sequence that was checked.
    """
    # Extract tile sequence
    tiles = [tile for _, _, tile in equation]
    
    # NOTE: Handle blank tiles - try all possible values
    # NOTE: Compound tiles must be declared when placed (format: "symbol:resolved")
    # If a compound tile doesn't have a declared value, it's an error
    blank_indices = [i for i, t in enumerate(tiles) if is_blank_tile(t)]
    locked_compound_values = {}  # Map index -> locked resolved value
    
    for i, (r, c, tile) in enumerate(equation):
        # Check if this is a locked compound tile (format: "symbol:resolved")
        resolved = _get_compound_resolved_value(tile)
        if resolved:
            # This compound tile has a declared value - use it
            locked_compound_values[i] = resolved
        elif tile in ['×/÷', '+/-']:
            # This is a compound tile without a declared value - error
            if return_resolved:
                return False, f"Compound tile '{tile}' at position {i} must be declared with a value when placed", None
            return False, f"Compound tile '{tile}' must be declared with a value when placed"
    
    # Generate all combinations for blank tiles only
    blank_combinations = []
    for idx in blank_indices:
        blank_value = get_blank_value(tiles[idx])
        if blank_value in BLANK_VALUES:
            blank_combinations.append([blank_value])
        else:
            # Invalid blank value
            if return_resolved:
                return False, f"Blank tile has invalid value: {blank_value}", None
            return False, f"Blank tile has invalid value: {blank_value}"
    
    # Try all combinations for blank tiles
    all_blank_combos = list(product(*blank_combinations)) if blank_combinations else [()]
    
    first_error = None
    first_resolved_sequence = None
    for blank_combo in all_blank_combos:
        # Create a test sequence with resolved tiles
        test_tiles = tiles[:]
        resolved_sequence = []
        blank_idx = 0
        for i, (r, c, tile) in enumerate(equation):
            if is_blank_tile(tile):
                resolved_value = blank_combo[blank_idx]
                test_tiles[i] = resolved_value
                resolved_sequence.append((r, c, resolved_value))
                blank_idx += 1
            elif i in locked_compound_values:
                # Use the declared value
                resolved_value = locked_compound_values[i]
                test_tiles[i] = resolved_value
                resolved_sequence.append((r, c, resolved_value))
            else:
                resolved_sequence.append((r, c, tile))
        
        # Validate this resolved sequence
        is_valid, error = validate_equation_sequence(test_tiles)
        if is_valid:
            if return_resolved:
                return True, None, resolved_sequence
            return True, None
        
        if first_error is None:
            first_error = error
            first_resolved_sequence = resolved_sequence
    
    # No valid combination found
    if return_resolved:
        return False, first_error or "No valid combination of blank tiles produces a valid equation", first_resolved_sequence
    if first_error:
        return False, first_error
    return False, "No valid combination of blank tiles produces a valid equation"


def validate_equation_sequence(tiles: List[str]) -> Tuple[bool, Optional[str]]:
    """
    Validate a sequence of tiles as a mathematical equation.
    Assumes all blanks and compounds are resolved.
    
    NOTE: Supports chained equalities (e.g., 7=7=7, 4+5=9=81÷9)
    """
    if not tiles:
        return False, "Empty equation"
    
    # NOTE: Equation cannot start or end with an equals sign
    if tiles[0] == '=':
        return False, "Equation cannot start with an equals sign"
    if tiles[-1] == '=':
        return False, "Equation cannot end with an equals sign"
    
    # NOTE: Equation must contain at least one equals sign
    equals_count = tiles.count('=')
    if equals_count == 0:
        return False, "Equation must contain at least one equals sign"
    
    # NOTE: Handle chained equalities (multiple equals signs)
    # Split by equals signs and validate each segment
    equals_indices = [i for i, tile in enumerate(tiles) if tile == '=']
    
    # Get all segments (between equals signs and at ends)
    segments = []
    start = 0
    for eq_idx in equals_indices:
        if eq_idx > start:
            segments.append(tiles[start:eq_idx])
        start = eq_idx + 1
    if start < len(tiles):
        segments.append(tiles[start:])
    
    if len(segments) < 2:
        return False, "Equation must have expressions on both sides of equals sign"
    
    # NOTE: Validate and calculate each segment
    segment_values = []
    for segment in segments:
        if not segment:
            return False, "Equation must have expressions on both sides of equals sign"
        valid, value = evaluate_expression(segment)
        if not valid:
            return False, f"Invalid expression segment: {value}"
        segment_values.append(value)
    
    # NOTE: All segments must be equal (chained equality)
    first_value = segment_values[0]
    for i, value in enumerate(segment_values[1:], 1):
        if abs(first_value - value) > 1e-9:  # Floating point comparison
            return False, f"Chained equality not balanced: {first_value} ≠ {value} (segment {i+1})"
    
    return True, None


def evaluate_expression(tokens: List[str]) -> Tuple[bool, float]:
    """
    Evaluate a mathematical expression from left to right.
    Returns (is_valid, result)
    
    NOTE: Multiplication and division are done before addition and subtraction.
    NOTE: Operations of same precedence are done left to right.
    NOTE: Division by zero is not allowed (except 0 ÷ anything = 0).
    """
    if not tokens:
        return False, "Empty expression"
    
    # NOTE: No leading plus sign
    if tokens[0] == '+':
        return False, "Plus sign cannot be placed in front of a number"
    
    # NOTE: No leading zeros
    if len(tokens) > 0 and tokens[0] == '0' and len(tokens) > 1 and is_number_tile(tokens[1]):
        return False, "Leading zeros are not allowed"
    
    # Parse tokens into numbers and operators
    # Combine consecutive number tiles into multi-digit numbers
    parsed = []
    i = 0
    while i < len(tokens):
        if is_number_tile(tokens[i]):
            # Collect consecutive number tiles
            number_str = tokens[i]
            i += 1
            while i < len(tokens) and is_number_tile(tokens[i]):
                number_str += tokens[i]
                i += 1
            # NOTE: Numbers with 4+ digits are not allowed
            if len(number_str) > 3:
                return False, f"Numbers with 4 or more digits are not allowed: {number_str}"
            
            parsed.append(('number', int(number_str)))
        elif tokens[i] in ['+', '-', '×', '÷']:
            parsed.append(('operator', tokens[i]))
            i += 1
        else:
            return False, f"Invalid token: {tokens[i]}"
    
    if not parsed:
        return False, "No valid tokens in expression"
    
    # Handle negative numbers (minus sign before a number)
    # NOTE: Minus is only a negative sign if it's at the start or after an operator
    # If it's after a number, it's a subtraction operator
    # NOTE: Negative numbers can be made from 1-20 or valid compound numbers
    normalized = []
    i = 0
    while i < len(parsed):
        if parsed[i][0] == 'operator' and parsed[i][1] == '-' and i + 1 < len(parsed) and parsed[i+1][0] == 'number':
            # Check if this is a negative sign (at start or after operator) or subtraction (after number)
            if i == 0 or (i > 0 and parsed[i-1][0] == 'operator'):
                # Negative number (at start or after operator)
                num_value = parsed[i+1][1]
                normalized.append(('number', -num_value))
                i += 2
            else:
                # Subtraction operator (after a number)
                normalized.append(parsed[i])
                i += 1
        else:
            normalized.append(parsed[i])
            i += 1
    
    # NOTE: No adjacent operators (except minus at start for negative)
    for i in range(len(normalized) - 1):
        if normalized[i][0] == 'operator' and normalized[i+1][0] == 'operator':
            return False, "Operators cannot be placed directly next to each other"
    
    # NOTE: Expression must start with a number (possibly negative)
    if normalized[0][0] != 'number':
        return False, "Expression must start with a number"
    
    # NOTE: Apply order of operations: × and ÷ first, then + and -
    # First pass: handle × and ÷
    result = [normalized[0]]
    i = 1
    while i < len(normalized):
        if normalized[i][0] == 'operator' and normalized[i][1] in ['×', '÷']:
            if i + 1 >= len(normalized) or normalized[i+1][0] != 'number':
                return False, "Operator must be followed by a number"
            
            left = result[-1][1]
            op = normalized[i][1]
            right = normalized[i+1][1]
            
            # NOTE: Division by zero is not allowed (except 0 ÷ anything = 0)
            if op == '÷':
                if right == 0:
                    return False, "Division by zero is not allowed"
                if left == 0:
                    # 0 ÷ anything = 0
                    result[-1] = ('number', 0)
                else:
                    result[-1] = ('number', left / right)
            else:  # ×
                result[-1] = ('number', left * right)
            
            i += 2
        else:
            result.append(normalized[i])
            i += 1
    
    # Second pass: handle + and - (left to right)
    final_value = result[0][1]
    i = 1
    while i < len(result):
        if result[i][0] == 'operator':
            if i + 1 >= len(result) or result[i+1][0] != 'number':
                return False, "Operator must be followed by a number"
            
            op = result[i][1]
            right = result[i+1][1]
            
            if op == '+':
                final_value += right
            else:  # -
                final_value -= right
            
            i += 2
        else:
            i += 1
    
    return True, final_value


def validate_multi_digit_adjacency(
    board: List[List[str]],
    row: int,
    col: int,
    tile: str,
    chars: Dict
) -> Optional[str]:
    """
    Validate that multi-digit number tiles (10-20) are not adjacent to other number tiles.
    
    NOTE: Multi-digit number tiles (10-20) cannot be placed adjacent to other number tiles.
    Must use single digits to form numbers (e.g., '1,7,2' instead of '17,2' or '2,17').
    """
    # Get the actual tile value (handle blank tiles)
    if is_blank_tile(tile):
        tile_value = get_blank_value(tile)
        if tile_value not in NUMBER_TILES:
            return None  # Not a number blank, skip
    else:
        tile_value = tile
    
    # Check if this is a multi-digit number tile (10-20)
    if tile_value not in NUMBER_TILES or len(tile_value) <= 1:
        return None  # Not a multi-digit tile, skip
    
    # Check all 4 adjacent positions
    neighbors = [(row-1, col), (row+1, col), (row, col-1), (row, col+1)]
    for nr, nc in neighbors:
        if 0 <= nr < 15 and 0 <= nc < 15:
            neighbor = board[nr][nc]
            if neighbor != ' ':
                # Get neighbor value (handle blank tiles)
                if is_blank_tile(neighbor):
                    neighbor_value = get_blank_value(neighbor)
                    if neighbor_value not in NUMBER_TILES:
                        continue  # Not a number, skip
                else:
                    neighbor_value = neighbor
                
                # Check if neighbor is a number tile
                if neighbor_value in NUMBER_TILES:
                    return f"Multi-digit number tile '{tile_value}' cannot be used adjacent to number tiles. Use single digits separated by commas (e.g., '1,7,2' instead of '2,17' or '17,2')"
    
    return None


def validate_number_formation(
    board: List[List[str]],
    row: int,
    col: int,
    chars: Dict
) -> Optional[str]:
    """
    Validate number formation rules.
    
    NOTE: 2-3 digits can form multi-digit numbers.
    NOTE: Cannot append digits to already-formed multi-digit numbers.
    NOTE: No leading zeros.
    NOTE: Cannot form numbers with 4+ digits.
    """
    tile = board[row][col]
    
    # Get the actual value if it's a blank
    if is_blank_tile(tile):
        value = get_blank_value(tile)
        if value not in NUMBER_TILES:
            return None  # Not a number blank, skip
        tile = value
    
    if not is_number_tile(tile):
        return None  # Not a number tile
    
    # Check horizontal formation
    # Find the start of the number sequence
    start_col = col
    while start_col > 0 and board[row][start_col - 1] != ' ':
        prev_tile = board[row][start_col - 1]
        if is_blank_tile(prev_tile):
            prev_value = get_blank_value(prev_tile)
            if prev_value not in NUMBER_TILES:
                break
        elif not is_number_tile(prev_tile):
            break
        start_col -= 1
    
    # Find the end of the number sequence
    end_col = col
    while end_col < 14 and board[row][end_col + 1] != ' ':
        next_tile = board[row][end_col + 1]
        if is_blank_tile(next_tile):
            next_value = get_blank_value(next_tile)
            if next_value not in NUMBER_TILES:
                break
        elif not is_number_tile(next_tile):
            break
        end_col += 1
    
    # Count digits in this number
    digit_count = 0
    number_str = ""
    for c in range(start_col, end_col + 1):
        t = board[row][c]
        if is_blank_tile(t):
            val = get_blank_value(t)
            if val in NUMBER_TILES:
                digit_count += 1
                number_str += val
        elif is_number_tile(t):
            digit_count += 1
            number_str += t
    
    # NOTE: Numbers with 4+ digits are not allowed
    if digit_count > 3:
        return f"Numbers with 4 or more digits are not allowed: {number_str}"
    
    # NOTE: No leading zeros
    if number_str.startswith('0') and len(number_str) > 1:
        return f"Leading zeros are not allowed: {number_str}"
    
    # Check vertical formation (same logic)
    start_row = row
    while start_row > 0 and board[start_row - 1][col] != ' ':
        prev_tile = board[start_row - 1][col]
        if is_blank_tile(prev_tile):
            prev_value = get_blank_value(prev_tile)
            if prev_value not in NUMBER_TILES:
                break
        elif not is_number_tile(prev_tile):
            break
        start_row -= 1
    
    end_row = row
    while end_row < 14 and board[end_row + 1][col] != ' ':
        next_tile = board[end_row + 1][col]
        if is_blank_tile(next_tile):
            next_value = get_blank_value(next_tile)
            if next_value not in NUMBER_TILES:
                break
        elif not is_number_tile(next_tile):
            break
        end_row += 1
    
    digit_count = 0
    number_str = ""
    for r in range(start_row, end_row + 1):
        t = board[r][col]
        if is_blank_tile(t):
            val = get_blank_value(t)
            if val in NUMBER_TILES:
                digit_count += 1
                number_str += val
        elif is_number_tile(t):
            digit_count += 1
            number_str += t
    
    if digit_count > 3:
        return f"Numbers with 4 or more digits are not allowed: {number_str}"
    
    if number_str.startswith('0') and len(number_str) > 1:
        return f"Leading zeros are not allowed: {number_str}"
    
    return None


def validate_operator_placement_single_with_new_tiles(
    board: List[List[str]],
    row: int,
    col: int,
    tile: str,
    new_tile_positions: Set[Tuple[int, int]],
    chars: Dict
) -> Optional[str]:
    """
    Validate operator placement for a single resolved tile, considering new tiles.
    This version checks neighbors that might also be new tiles.
    """
    if tile not in ['+', '-', '×', '÷', '=']:
        return None  # Not an operator
    
    # NOTE: Check for adjacent operators
    # NOTE: Operators cannot be adjacent to each other, EXCEPT:
    # - A minus sign at the start of an expression (before any number) is allowed
    # - So -a+b is OK (negative sign - at start, followed by number a, then operator +)
    # - But a+-b, a/-b, a*-b are NOT OK (operator next to operator)
    # - And compound operators cannot be adjacent to other operators either
    neighbors = [(row-1, col), (row+1, col), (row, col-1), (row, col+1)]
    for nr, nc in neighbors:
        if 0 <= nr < 15 and 0 <= nc < 15:
            neighbor = board[nr][nc]
            if neighbor != ' ':
                # Check if neighbor is an operator or compound operator
                neighbor_is_operator = False
                neighbor_resolved_values = []
                
                if is_blank_tile(neighbor):
                    neighbor_value = get_blank_value(neighbor)
                    if neighbor_value in ['+', '-', '×', '÷', '=']:
                        neighbor_is_operator = True
                        neighbor_resolved_values = [neighbor_value]
                elif neighbor in ['+', '-', '×', '÷', '=']:
                    neighbor_is_operator = True
                    neighbor_resolved_values = [neighbor]
                elif neighbor in ['×/÷', '+/-']:
                    # Compound operator - check all possible resolved values
                    neighbor_is_operator = True
                    if neighbor == '+/-':
                        neighbor_resolved_values = ['+', '-']
                    else:  # ×/÷
                        neighbor_resolved_values = ['×', '÷']
                
                if neighbor_is_operator:
                    # NOTE: Operators cannot be adjacent, EXCEPT:
                    # - A minus sign at the very start of an expression (before any number) is OK
                    # - So -a+b is OK (negative sign at start, number a, then operator +)
                    # - But a+-b, a/-b, a*-b are NOT OK (operator next to operator)
                    # - Also, = can be adjacent to operators that make negative numbers (special case for equations)
                    
                    # Check if this tile is a minus at the start of an expression (not after an operator)
                    this_is_negative_sign_at_start = (tile == '-' and _is_at_start_of_expression(board, row, col))
                    
                    # Check all possible resolved values of neighbor
                    all_invalid = True
                    for neighbor_opt in neighbor_resolved_values:
                        # If neighbor is a minus at the start of an expression, it's OK
                        neighbor_is_negative_sign_at_start = (neighbor_opt == '-' and _is_at_start_of_expression(board, nr, nc))
                        
                        # Special case: = can be adjacent to operators that make negative numbers
                        # (e.g., 3 = -1 or 3 = (+/-)1)
                        if tile == '=' or neighbor_opt == '=':
                            # If the other operator is making a negative number, it's OK
                            if tile == '=':
                                other_is_negative = (neighbor_opt == '-' and _is_making_negative_number(board, nr, nc))
                            else:
                                other_is_negative = (tile == '-' and _is_making_negative_number(board, row, col))
                            
                            if other_is_negative:
                                all_invalid = False
                                break
                        
                        # If either this tile or neighbor is a negative sign at the start, it's OK
                        if this_is_negative_sign_at_start or neighbor_is_negative_sign_at_start:
                            all_invalid = False
                            break
                    
                    # If all combinations result in operators adjacent to operators, it's invalid
                    if all_invalid:
                        return "Operators cannot be placed directly next to each other"
    
    # NOTE: Plus sign cannot be placed in front of a number (at start of expression)
    if tile == '+':
        # Check if plus is at the start of an expression (nothing before it)
        # and there's a number after it
        is_at_start = _is_at_start_of_expression(board, row, col)
        if is_at_start:
            # Check if there's a number after the plus sign
            has_number_after = False
            # Check right
            if col < 14:
                right = board[row][col+1]
                if right != ' ':
                    if is_number_tile(right) or (is_blank_tile(right) and get_blank_value(right) in NUMBER_TILES):
                        has_number_after = True
            # Check down
            if not has_number_after and row < 14:
                down = board[row+1][col]
                if down != ' ':
                    if is_number_tile(down) or (is_blank_tile(down) and get_blank_value(down) in NUMBER_TILES):
                        has_number_after = True
            if has_number_after:
                return "Plus sign cannot be placed in front of a number"
    
    # NOTE: Minus sign cannot be placed in front of 0
    # NOTE: This applies both at the start of an expression AND when making a negative number
    if tile == '-':
        # Check if minus is making a negative number (at start or after operator)
        is_making_negative = _is_making_negative_number(board, row, col)
        if is_making_negative:
            # Check if there's a 0 after the minus sign
            has_zero_after = False
            # Check right
            if col < 14:
                right = board[row][col+1]
                if right != ' ':
                    if right == '0' or (is_blank_tile(right) and get_blank_value(right) == '0'):
                        has_zero_after = True
            # Check down
            if not has_zero_after and row < 14:
                down = board[row+1][col]
                if down != ' ':
                    if down == '0' or (is_blank_tile(down) and get_blank_value(down) == '0'):
                        has_zero_after = True
            if has_zero_after:
                return "Minus sign cannot be placed in front of 0"
    
    return None


def validate_operator_placement_single(
    board: List[List[str]],
    row: int,
    col: int,
    tile: str,
    chars: Dict
) -> Optional[str]:
    """
    Validate operator placement for a single resolved tile (not compound).
    This is the core validation logic.
    
    NOTE: Operators cannot be placed directly next to each other.
    NOTE: Plus sign cannot be placed in front of a number.
    NOTE: Minus sign cannot be placed in front of 0.
    NOTE: Minus sign can be placed in front of numbers 1-16, 20, or formed numbers.
    """
    # tile is already resolved (not a compound tile, not a blank)
    if tile not in ['+', '-', '×', '÷', '=']:
        return None  # Not an operator
    
    # NOTE: Check for adjacent operators
    # NOTE: Operators cannot be adjacent to each other, EXCEPT:
    # - A minus sign at the start of an expression (before any number) is allowed
    # - So -a+b is OK (negative sign - at start, followed by number a, then operator +)
    # - But a+-b, a/-b, a*-b are NOT OK (operator next to operator)
    # - And compound operators cannot be adjacent to other operators either
    neighbors = [(row-1, col), (row+1, col), (row, col-1), (row, col+1)]
    for nr, nc in neighbors:
        if 0 <= nr < 15 and 0 <= nc < 15:
            neighbor = board[nr][nc]
            if neighbor != ' ':
                # Check if neighbor is an operator or compound operator
                neighbor_is_operator = False
                neighbor_resolved_values = []
                
                if is_blank_tile(neighbor):
                    neighbor_value = get_blank_value(neighbor)
                    if neighbor_value in ['+', '-', '×', '÷', '=']:
                        neighbor_is_operator = True
                        neighbor_resolved_values = [neighbor_value]
                elif neighbor in ['+', '-', '×', '÷', '=']:
                    neighbor_is_operator = True
                    neighbor_resolved_values = [neighbor]
                elif neighbor in ['×/÷', '+/-']:
                    # Compound operator - check all possible resolved values
                    neighbor_is_operator = True
                    if neighbor == '+/-':
                        neighbor_resolved_values = ['+', '-']
                    else:  # ×/÷
                        neighbor_resolved_values = ['×', '÷']
                
                if neighbor_is_operator:
                    # NOTE: Operators cannot be adjacent, EXCEPT:
                    # - A minus sign at the very start of an expression (before any number) is OK
                    # - So -a+b is OK (negative sign at start, number a, then operator +)
                    # - But a+-b, a/-b, a*-b are NOT OK (operator next to operator)
                    # - Also, = can be adjacent to operators that make negative numbers (special case for equations)
                    
                    # Check if this tile is a minus at the start of an expression (not after an operator)
                    this_is_negative_sign_at_start = (tile == '-' and _is_at_start_of_expression(board, row, col))
                    
                    # Check all possible resolved values of neighbor
                    all_invalid = True
                    for neighbor_opt in neighbor_resolved_values:
                        # If neighbor is a minus at the start of an expression, it's OK
                        neighbor_is_negative_sign_at_start = (neighbor_opt == '-' and _is_at_start_of_expression(board, nr, nc))
                        
                        # Special case: = can be adjacent to operators that make negative numbers
                        # (e.g., 3 = -1 or 3 = (+/-)1)
                        if tile == '=' or neighbor_opt == '=':
                            # If the other operator is making a negative number, it's OK
                            if tile == '=':
                                other_is_negative = (neighbor_opt == '-' and _is_making_negative_number(board, nr, nc))
                            else:
                                other_is_negative = (tile == '-' and _is_making_negative_number(board, row, col))
                            
                            if other_is_negative:
                                all_invalid = False
                                break
                        
                        # If either this tile or neighbor is a negative sign at the start, it's OK
                        if this_is_negative_sign_at_start or neighbor_is_negative_sign_at_start:
                            all_invalid = False
                            break
                    
                    # If all combinations result in operators adjacent to operators, it's invalid
                    if all_invalid:
                        return "Operators cannot be placed directly next to each other"
    
    # NOTE: Plus sign cannot be placed in front of a number
    # NOTE: This applies both at the start of an expression AND when after an operator (making a positive number)
    if tile == '+':
        # Check if plus is at the start of an expression OR after an operator (making a positive number)
        is_at_start = _is_at_start_of_expression(board, row, col)
        is_after_operator = False
        if not is_at_start:
            # Check if there's an operator before it
            # Check left
            if col > 0:
                left = board[row][col-1]
                if left != ' ':
                    if left in ['+', '-', '×', '÷', '='] or (is_blank_tile(left) and get_blank_value(left) in ['+', '-', '×', '÷', '=']):
                        is_after_operator = True
            # Check up
            if not is_after_operator and row > 0:
                up = board[row-1][col]
                if up != ' ':
                    if up in ['+', '-', '×', '÷', '='] or (is_blank_tile(up) and get_blank_value(up) in ['+', '-', '×', '÷', '=']):
                        is_after_operator = True
        
        if is_at_start or is_after_operator:
            # Check if there's a number after the plus sign
            has_number_after = False
            # Check right
            if col < 14:
                right = board[row][col+1]
                if right != ' ':
                    if is_number_tile(right) or (is_blank_tile(right) and get_blank_value(right) in NUMBER_TILES):
                        has_number_after = True
            # Check down
            if not has_number_after and row < 14:
                down = board[row+1][col]
                if down != ' ':
                    if is_number_tile(down) or (is_blank_tile(down) and get_blank_value(down) in NUMBER_TILES):
                        has_number_after = True
            if has_number_after:
                return "Plus sign cannot be placed in front of a number"
    
    # NOTE: Minus sign cannot be placed in front of 0
    # NOTE: This applies both at the start of an expression AND when making a negative number
    if tile == '-':
        # Check if minus is making a negative number (at start or after operator)
        is_making_negative = _is_making_negative_number(board, row, col)
        if is_making_negative:
            # Check if there's a 0 after the minus sign
            has_zero_after = False
            # Check right
            if col < 14:
                right = board[row][col+1]
                if right != ' ':
                    if right == '0' or (is_blank_tile(right) and get_blank_value(right) == '0'):
                        has_zero_after = True
            # Check down
            if not has_zero_after and row < 14:
                down = board[row+1][col]
                if down != ' ':
                    if down == '0' or (is_blank_tile(down) and get_blank_value(down) == '0'):
                        has_zero_after = True
            if has_zero_after:
                return "Minus sign cannot be placed in front of 0"
    
    return None


def _resolve_sequence_for_display(sequence: List[Tuple[int, int, str]], board: List[List[str]]) -> List[Tuple[int, int, str]]:
    """
    Resolve compound tiles and blank tiles in a sequence for display.
    For compound tiles, shows the resolved value from the board (if already resolved),
    otherwise shows the first possible value.
    For blank tiles, shows the resolved value.
    """
    resolved = []
    for r, c, tile in sequence:
        if tile in ['×/÷', '+/-']:
            # Check if the board has a resolved value for this compound tile
            board_tile = board[r][c]
            if board_tile in ['+', '-', '×', '÷']:
                # Board has a resolved value (from validation), use it
                resolved.append((r, c, board_tile))
            else:
                # Still a compound tile, show the first option
                if tile == '+/-':
                    resolved.append((r, c, '+'))  # Show first option
                else:  # ×/÷
                    resolved.append((r, c, '×'))  # Show first option
        elif is_blank_tile(tile):
            # Show blank tile value
            blank_value = get_blank_value(tile)
            resolved.append((r, c, blank_value))
        else:
            resolved.append((r, c, tile))
    return resolved


def validate_operator_placement(
    board: List[List[str]],
    row: int,
    col: int,
    chars: Dict
) -> Optional[str]:
    """
    Validate operator placement rules.
    Handles blank tiles by resolving them first.
    """
    tile = board[row][col]
    
    # Get the actual value if it's a blank
    if is_blank_tile(tile):
        value = get_blank_value(tile)
        if value not in ['+', '-', '×', '÷', '=']:
            return None  # Not an operator blank
        tile = value
    
    # If it's a compound tile, it should have been handled by the caller
    if tile in ['×/÷', '+/-']:
        return None  # Should be handled separately
    
    # Use the single-tile validation
    return validate_operator_placement_single(board, row, col, tile, chars)


def _is_at_start_of_expression(board: List[List[str]], row: int, col: int) -> bool:
    """Check if position is at the start of an expression (for negative numbers)"""
    # Check horizontal
    if col > 0 and board[row][col-1] != ' ':
        return False
    # Check vertical
    if row > 0 and board[row-1][col] != ' ':
        return False
    return True


def _is_making_negative_number(board: List[List[str]], row: int, col: int) -> bool:
    """Check if minus sign is making a negative number (at start or after operator)"""
    # Check if there's nothing before it (start of expression)
    if _is_at_start_of_expression(board, row, col):
        return True
    
    # Check if there's an operator before it (after operator = making negative)
    # Check left
    if col > 0:
        left = board[row][col-1]
        if left != ' ':
            if left in ['+', '-', '×', '÷', '='] or (is_blank_tile(left) and get_blank_value(left) in ['+', '-', '×', '÷', '=']):
                return True
    # Check up
    if row > 0:
        up = board[row-1][col]
        if up != ' ':
            if up in ['+', '-', '×', '÷', '='] or (is_blank_tile(up) and get_blank_value(up) in ['+', '-', '×', '÷', '=']):
                return True
    
    # If there's a number before it, it's subtraction, not negative
    return False


def _has_number_before(board: List[List[str]], row: int, col: int) -> bool:
    """Check if there's a number tile before this position"""
    # Check left
    if col > 0:
        left = board[row][col-1]
        if left != ' ':
            if is_number_tile(left) or (is_blank_tile(left) and get_blank_value(left) in NUMBER_TILES):
                return True
    # Check up
    if row > 0:
        up = board[row-1][col]
        if up != ' ':
            if is_number_tile(up) or (is_blank_tile(up) and get_blank_value(up) in NUMBER_TILES):
                return True
    return False


def _has_valid_number_after(board: List[List[str]], row: int, col: int, chars: Dict) -> bool:
    """Check if there's a valid number after minus sign (for making negative numbers)"""
    # Check right
    if col < 14:
        right = board[row][col+1]
        if right != ' ':
            # Cannot make 0 negative
            if right == '0' or (is_blank_tile(right) and get_blank_value(right) == '0'):
                return False
            if is_number_tile(right):
                # Check if it's a valid number (1-20 or part of formed number)
                return _is_valid_negative_number(board, row, col+1, True, chars)
            elif is_blank_tile(right):
                val = get_blank_value(right)
                if val in NUMBER_TILES:
                    # Cannot make 0 negative
                    if val == '0':
                        return False
                    return _is_valid_negative_number(board, row, col+1, True, chars)
    # Check down
    if row < 14:
        down = board[row+1][col]
        if down != ' ':
            # Cannot make 0 negative
            if down == '0' or (is_blank_tile(down) and get_blank_value(down) == '0'):
                return False
            if is_number_tile(down):
                return _is_valid_negative_number(board, row+1, col, False, chars)
            elif is_blank_tile(down):
                val = get_blank_value(down)
                if val in NUMBER_TILES:
                    # Cannot make 0 negative
                    if val == '0':
                        return False
                    return _is_valid_negative_number(board, row+1, col, False, chars)
    return False


def _is_valid_negative_number(
    board: List[List[str]],
    row: int,
    col: int,
    is_horizontal: bool,
    chars: Dict
) -> bool:
    """
    Check if a number can be made negative.
    NOTE: Minus can be placed before numbers 1-20 or valid compound numbers.
    """
    # Extract the full number
    if is_horizontal:
        start_col = col
        while start_col > 0 and board[row][start_col-1] != ' ':
            prev = board[row][start_col-1]
            if is_number_tile(prev) or (is_blank_tile(prev) and get_blank_value(prev) in NUMBER_TILES):
                start_col -= 1
            else:
                break
        
        number_str = ""
        c = start_col
        while c < 15 and board[row][c] != ' ':
            t = board[row][c]
            if is_number_tile(t):
                number_str += t
            elif is_blank_tile(t):
                val = get_blank_value(t)
                if val in NUMBER_TILES:
                    number_str += val
                else:
                    break
            else:
                break
            c += 1
    else:
        start_row = row
        while start_row > 0 and board[start_row-1][col] != ' ':
            prev = board[start_row-1][col]
            if is_number_tile(prev) or (is_blank_tile(prev) and get_blank_value(prev) in NUMBER_TILES):
                start_row -= 1
            else:
                break
        
        number_str = ""
        r = start_row
        while r < 15 and board[r][col] != ' ':
            t = board[r][col]
            if is_number_tile(t):
                number_str += t
            elif is_blank_tile(t):
                val = get_blank_value(t)
                if val in NUMBER_TILES:
                    number_str += val
                else:
                    break
            else:
                break
            r += 1
    
    if not number_str:
        return False
    
    # Check if it's a number 1-20 or a formed number
    try:
        num = int(number_str)
        # Numbers 1-20 are valid
        if 1 <= num <= 20:
            return True
        # Formed numbers (2-3 digits) are also valid
        if 2 <= len(number_str) <= 3:
            return True
    except ValueError:
        pass
    
    return False

r