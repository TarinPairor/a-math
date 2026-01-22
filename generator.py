"""
Generator module for finding valid moves through existing equals signs on the board.
Uses v3.py algorithms to generate constrained equations and maps them to actual plays.
"""

from typing import List, Tuple, Optional, Set, Dict
from collections import Counter
import sys
import os

# Import v3 functions (from algos directory)
from algos.v3 import (
    build_inverted_tree, build_custom_tree, get_terminal_paths_tree,
    tiles_to_counts, tiles_to_multiset, unordered_partitions, prune_tree_by_counts,
    get_terminal_paths_graph, paths_to_expressions, generate_all_equations,
    S, O, DIVIDE, DASH, EQ, M, W, Z, T
)
from simpleeval import simple_eval
import re

# Define eval_eq and constraint_eq locally (same as v3.py)
def eval_eq(s):
    s1 = re.sub(',', '', s)
    s2 = re.sub('\(=\)', '=', s1)
    s3 = re.sub('=', '==', s2)
    return simple_eval(s3)

def constraint_eq(s, lhs_len, rhs_len):
    a, b = s.split('(=)')[0], s.split('(=)')[1]
    a = [x for x in re.split(',', a) if x]
    b = [x for x in re.split(',', b) if x]
    return len(a) <= lhs_len and len(b) <= rhs_len

from validation import is_blank_tile, get_blank_value
from scoring import calculate_play_score


def _get_compound_resolved_value(tile: str) -> Optional[str]:
    """Get the resolved value of a compound tile, or None if not a compound tile."""
    if ':' in tile:
        parts = tile.split(':', 1)
        if len(parts) == 2 and parts[0] in ['×/÷', '+/-']:
            return parts[1]  # Return the resolved value
    return None


def normalize_tile(tile: str) -> Optional[str]:
    """
    Normalize a tile from the board to its resolved value.
    - Blank tiles (?) -> their value
    - Compound tiles (with :) -> their resolved value  
    - Regular tiles -> as-is
    - Empty -> None
    """
    if tile == ' ':
        return None
    
    # Blank tile
    if is_blank_tile(tile):
        return get_blank_value(tile)
    
    # Compound tile with resolved value
    resolved = _get_compound_resolved_value(tile)
    if resolved:
        return resolved
    
    # Regular tile
    return tile


def find_equals_on_board(board: List[List[str]]) -> List[Tuple[int, int]]:
    """Find all positions of '=' signs on the board."""
    equals_positions = []
    for row in range(15):
        for col in range(15):
            tile = board[row][col]
            if tile == '=':
                equals_positions.append((row, col))
            elif is_blank_tile(tile) and get_blank_value(tile) == '=':
                equals_positions.append((row, col))
            elif tile == 'EQ':  # Not sure if this exists, but just in case
                equals_positions.append((row, col))
    return equals_positions


def get_green_highlight_cells_from_equals(board: List[List[str]], eq_row: int, eq_col: int) -> Set[Tuple[int, int]]:
    """
    Get green highlight cells from a specific equals sign using board_visualizer logic.
    """
    green_cells = set()
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]  # up, down, left, right
    
    def is_occupied(row, col):
        return 0 <= row < 15 and 0 <= col < 15 and board[row][col] != ' '
    
    def count_contiguous_in_direction(row, col, drow, dcol):
        count = 0
        check_row, check_col = row + drow, col + dcol
        while 0 <= check_row < 15 and 0 <= check_col < 15:
            if is_occupied(check_row, check_col):
                count += 1
                check_row += drow
                check_col += dcol
            else:
                break
        return count
    
    # Extend line in all 4 directions from the equals sign
    for drow, dcol in directions:
        cells_counted = 0
        check_row, check_col = eq_row + drow, eq_col + dcol
        
        # Continue until we've counted 7 cells or reached board boundary
        while cells_counted < 7 and 0 <= check_row < 15 and 0 <= check_col < 15:
            if is_occupied(check_row, check_col):
                # Skip occupied cell, continue to next
                check_row += drow
                check_col += dcol
                continue
            
            # Check if this empty cell should stop the line
            should_stop = False
            if drow != 0:  # Vertical line (up or down)
                # Check perpendicular axis: left and right
                count_left = count_contiguous_in_direction(check_row, check_col, 0, -1)
                count_right = count_contiguous_in_direction(check_row, check_col, 0, 1)
                # Stop if: (1 on left AND 0 on right) OR (0 on left AND 1 on right) OR (1 on both)
                if (count_left == 1 and count_right == 0) or (count_left == 0 and count_right == 1) or (count_left == 1 and count_right == 1):
                    should_stop = True
            else:  # Horizontal line (left or right)
                # Check perpendicular axis: up and down
                count_above = count_contiguous_in_direction(check_row, check_col, -1, 0)
                count_below = count_contiguous_in_direction(check_row, check_col, 1, 0)
                # Stop if: (1 above AND 0 below) OR (0 above AND 1 below) OR (1 on both)
                if (count_above == 1 and count_below == 0) or (count_above == 0 and count_below == 1) or (count_above == 1 and count_below == 1):
                    should_stop = True
            
            if should_stop:
                # Stop before this cell
                break
            
            # Mark this empty cell as green
            green_cells.add((check_row, check_col))
            cells_counted += 1
            check_row += drow
            check_col += dcol
    
    return green_cells


def get_valid_paths_through_equals(board: List[List[str]], eq_row: int, eq_col: int) -> List[Tuple[List[Tuple[int, int]], List[Tuple[int, int]], bool]]:
    """
    Get valid paths (green cells) going through an equals sign.
    Uses board_visualizer logic to find green cells, then builds paths.
    Path includes both existing tiles and green empty cells in a contiguous sequence.
    
    Returns:
        List of (lhs_path, rhs_path, is_horizontal) tuples
        - lhs_path: list of (row, col) going left (horizontal) or up (vertical)
        - rhs_path: list of (row, col) going right (horizontal) or down (vertical)
        - is_horizontal: True if horizontal path, False if vertical
        Returns both horizontal AND vertical if both are valid
    """
    green_cells = get_green_highlight_cells_from_equals(board, eq_row, eq_col)
    paths = []
    
    # Horizontal path (left and right)
    lhs_horiz = []
    rhs_horiz = []
    
    # Left side (going left from =)
    # Path should be: [tile closest to =, next cell, next cell, ...]
    # So we iterate from = going left, and add cells in order
    for c in range(eq_col - 1, -1, -1):
        is_tile = board[eq_row][c] != ' '
        is_green = (eq_row, c) in green_cells
        if is_tile or is_green:
            lhs_horiz.append((eq_row, c))
        else:
            # Hit non-green empty cell, stop
            break
    
    # Right side (going right from =)
    for c in range(eq_col + 1, 15):
        is_tile = board[eq_row][c] != ' '
        is_green = (eq_row, c) in green_cells
        if is_tile or is_green:
            rhs_horiz.append((eq_row, c))
        else:
            break
    
    # Add horizontal path if it has any cells
    if lhs_horiz or rhs_horiz:
        paths.append((lhs_horiz, rhs_horiz, True))
    
    # Vertical path (up and down)
    lhs_vert = []
    rhs_vert = []
    
    # Up side (going up from =)
    # Path should be: [tile closest to =, next cell, next cell, ...]
    # So we iterate from = going up, and add cells in order
    for r in range(eq_row - 1, -1, -1):
        is_tile = board[r][eq_col] != ' '
        is_green = (r, eq_col) in green_cells
        if is_tile or is_green:
            lhs_vert.append((r, eq_col))
        else:
            # Hit non-green empty cell, stop
            break
    
    # Down side (going down from =)
    for r in range(eq_row + 1, 15):
        is_tile = board[r][eq_col] != ' '
        is_green = (r, eq_col) in green_cells
        if is_tile or is_green:
            rhs_vert.append((r, eq_col))
        else:
            break
    
    # Add vertical path if it has any cells
    if lhs_vert or rhs_vert:
        paths.append((lhs_vert, rhs_vert, False))
    
    return paths


def build_level_filter_arr(path: List[Tuple[int, int]], board: List[List[str]], reverse: bool = False) -> List:
    """
    Build level_filter_arr for tree building from a path of board positions.
    The path represents positions going from = in the direction (left/up for LHS, right/down for RHS).
    Each position in the path maps to a level in the tree.
    
    Args:
        path: List of (row, col) positions (including empty cells)
        board: The game board
        reverse: If True, reverse the path (for LHS in inverted tree)
    
    Returns:
        List of length 16 with normalized tiles or None for empty squares
        Format: [S, level1, level2, ..., level15]
    """
    arr = [None] * 16
    arr[0] = S  # First element must be S
    
    # Process path to get normalized tiles (each position in path = one level)
    normalized_path = []
    for row, col in path:
        tile = board[row][col]
        if tile != ' ':
            normalized = normalize_tile(tile)
            if normalized:
                # Keep the concrete value - v3.py handles both concrete values and type tokens
                # For numbers: '0', '1'-'9', '10'-'20' (as strings)
                # For operators: '+', '-', '*', '/', '='
                normalized_path.append(normalized)
            else:
                normalized_path.append(None)  # Keep None for empty/unresolved
        else:
            normalized_path.append(None)  # Empty square (green cell but no tile)
    
    # For LHS (inverted tree): reverse the path
    # The path order is: [tile closest to =, next cell, next cell, ...]
    # After reverse: [..., next cell, next cell, tile closest to =]
    # But we want the tile closest to = at index 1 in the array
    # So for LHS, we need to reverse, but then the first tile should be at index 1
    
    # Actually, let me think: for LHS going up from H9 (row 8, has =)
    # Path is [H8(6), H7(empty), H6(empty), ...] - tile closest to = is FIRST
    # For inverted tree, we reverse: [..., H6(empty), H7(empty), H8(6)]
    # But we want ['S', '6', None, None, ...]
    # So '6' should be at position 1, which means it should be the FIRST element
    
    # I think the solution is: for LHS, don't reverse. The path is already
    # in the order we want: tile closest to = is first.
    # For RHS, also don't reverse: tile closest to = is first.
    
    # But wait, the user said "lhs counts in reverse" - maybe they mean
    # the tree construction handles it? Let me try not reversing for now.
    
    # Actually, let me check: if we have path [H8(6), H7(empty), H6(empty)]
    # normalized_path = ['6', None, None]
    # For LHS (reverse=True): reversed = [None, None, '6']
    # Array becomes ['S', None, None, '6', ...] - wrong!
    
    # If we don't reverse: array becomes ['S', '6', None, None, ...] - correct!
    
    # So for LHS, we should NOT reverse. The path is already correct.
    # But wait, that contradicts the "reverse" parameter name...
    
    # Let me try: for LHS, we want to reverse the VISUAL order but keep
    # the array order. Actually, I think the issue is simpler:
    # For LHS, the path represents cells going left/up from =
    # The first cell (closest to =) should be at array index 1
    # So we should NOT reverse
    
    # For now, let's try: only reverse if we want to, but ensure
    # the first non-None value is at index 1
    # For LHS (inverted tree): path is [tile closest to =, next cell, ...]
    # We want ['S', tile, ...] with tile at index 1
    # So DON'T reverse - the path is already correct with tile closest to = first
    # The inverted tree handles the internal structure, but the array should have
    # the tile closest to = at index 1
    # For RHS: same logic - tile closest to = should be at index 1
    if False:  # Don't reverse - path order is already correct for both LHS and RHS
        normalized_path = normalized_path[::-1]
    
    # Fill arr starting from index 1 (level 1, level 2, etc.)
    # The first element in normalized_path (tile closest to =) goes at index 1
    for i, tile in enumerate(normalized_path):
        if i + 1 < 16:
            arr[i + 1] = tile
    
    return arr




def generate_moves_for_equals(
    board: List[List[str]],
    rack: List[str],
    chars: Dict,
    bonus: Dict,
    eq_row: int,
    eq_col: int,
    lhs_path: List[Tuple[int, int]],
    rhs_path: List[Tuple[int, int]],
    is_horizontal: bool,
    debug: bool = False
) -> Tuple[List[Tuple[str, str, str, int]], Dict]:
    """
    Generate valid moves for a specific equals sign position.
    
    Returns:
        (moves, debug_info) where moves is list of (coord, move_str, leave, score) tuples
        and debug_info contains debugging information
    """
    moves = []
    debug_info = {}
    
    # Build level_filter_arr for LHS (inverted tree, reversed)
    lhs_filter = build_level_filter_arr(lhs_path, board, reverse=True)
    
    # Build level_filter_arr for RHS (custom tree, normal direction)
    rhs_filter = build_level_filter_arr(rhs_path, board, reverse=False)
    
    if debug:
        debug_info['lhs_filter'] = lhs_filter
        debug_info['rhs_filter'] = rhs_filter
    
    # Build trees
    inverted_G, _ = build_inverted_tree(lhs_filter)
    custom_G, _ = build_custom_tree(rhs_filter)
    
    # Get constrained equations using the rack
    # Convert rack tiles to format expected by generate_all_equations
    # The function expects strings like '0', '1', '2', '+', '-', '*', '/', '='
    # NOTE: Existing tiles on the board (in level_filter_arr) are handled automatically by v3.py
    # So we only need to include rack tiles in tiles_arr
    rack_tiles = []
    for tile in rack:
        if tile in ['+/-', '×/÷']:
            # Compound tiles - skip for equation generation (they need to be resolved first)
            continue
        elif is_blank_tile(tile):
            # Blank tiles - convert to their value
            blank_val = get_blank_value(tile)
            if blank_val:
                rack_tiles.append(str(blank_val) if blank_val.isdigit() else blank_val)
        elif tile in ['×', '÷']:
            # Convert Unicode operators to ASCII
            if tile == '×':
                rack_tiles.append('*')
            elif tile == '÷':
                rack_tiles.append('/')
        else:
            # Regular tile - use as string
            rack_tiles.append(str(tile))
    
    # tiles_arr only contains rack tiles - existing tiles are in level_filter_arr
    tiles_arr = rack_tiles
    
    debug_info['tiles_arr'] = tiles_arr.copy()
    debug_info['rack_tiles'] = rack_tiles.copy()
    
    # Generate equations
    try:
        equations = generate_all_equations(
            inverted_G=inverted_G,
            custom_G=custom_G,
            tiles_arr=tiles_arr,  # Use tiles_arr which includes existing tiles from board
            T=T, S=S,
            lhs_level_filter=lhs_filter,  # Pass the level filter arrays
            rhs_level_filter=rhs_filter
        )
        debug_info['all_eqs'] = equations
        debug_info['first_10_eqs'] = equations[:10] if len(equations) > 0 else []
    except Exception as e:
        debug_info['error'] = str(e)
        return [], debug_info
    
    # Filter to valid equations (syntactically correct)
    correct_eqs = []
    for eq in equations:
        # Check if equation is valid (evaluates correctly)
        try:
            if eval_eq(eq):
                correct_eqs.append(eq)
        except:
            continue
    
    debug_info['correct_eqs'] = correct_eqs
    debug_info['first_10_correct_eqs'] = correct_eqs[:10] if len(correct_eqs) > 10 else correct_eqs
    
    # Filter by path length constraints
    lhs_len = len(lhs_path)
    rhs_len = len(rhs_path)
    
    constrained_eqs = []
    for eq in correct_eqs:
        if constraint_eq(eq, lhs_len, rhs_len):
            constrained_eqs.append(eq)
    
    debug_info['constrained_eqs'] = constrained_eqs
    
    valid_eqs = constrained_eqs
    
    # For each valid equation, create a move
    for eq_str in valid_eqs:
        lhs_part, rhs_part = eq_str.split('(=)')
        lhs_tokens = [x.strip() for x in lhs_part.split(',') if x.strip()]
        rhs_tokens = [x.strip() for x in rhs_part.split(',') if x.strip()]
        
        # Reverse LHS tokens (since they go from right to left)
        lhs_tokens = lhs_tokens[::-1]
        
        # Determine starting coordinate
        if is_horizontal:
            # Start from leftmost position
            start_col = eq_col - len(lhs_tokens)
            start_row = eq_row
            coord = f"{start_row + 1}{chr(ord('A') + start_col)}"
            
            # Build move string
            move_parts = []
            for i, token in enumerate(lhs_tokens):
                move_parts.append(token)
            move_parts.append('.')  # The = sign
            for token in rhs_tokens:
                move_parts.append(token)
            
            move_str = ','.join(move_parts)
        else:
            # Vertical
            start_row = eq_row - len(lhs_tokens)
            start_col = eq_col
            coord = f"{chr(ord('A') + start_col)}{start_row + 1}"
            
            move_parts = []
            for token in lhs_tokens:
                move_parts.append(token)
            move_parts.append('.')  # The = sign
            for token in rhs_tokens:
                move_parts.append(token)
            
            move_str = ','.join(move_parts)
        
        # Calculate score
        # Build new_tiles list for scoring
        new_tiles_list = []
        for token in lhs_tokens + rhs_tokens:
            # Find position where this token would be placed
            # This is simplified - in reality we'd need to track positions more carefully
            pass
        
        # For now, use a simplified score calculation
        # TODO: Properly calculate score using calculate_play_score
        score = 0
        
        # Calculate leave
        leave_tiles = rack.copy()
        for token in lhs_tokens + rhs_tokens:
            if token in leave_tiles:
                leave_tiles.remove(token)
        leave = ','.join(leave_tiles) if leave_tiles else ''
        
        moves.append((coord, move_str, leave, score))
    
    return moves, debug_info


def coord_to_string(row: int, col: int, is_horizontal: bool) -> str:
    """Convert row, col to coordinate string."""
    letter = chr(ord('A') + col)
    number = str(row + 1)
    if is_horizontal:
        return f"{number}{letter}"
    else:
        return f"{letter}{number}"


def generate_moves(game, debug: bool = True) -> Tuple[List[Tuple[str, str, str, int]], Dict]:
    """
    Main function to generate all valid moves.
    
    Args:
        game: AMathGame instance
        debug: If True, include debug information
    
    Returns:
        (moves, debug_info) where moves is list of (coord, move_str, leave, score) tuples
    """
    all_moves = []
    all_debug_info = {}
    
    # Find all equals signs on the board
    equals_positions = find_equals_on_board(game.board)
    
    if debug:
        eq_coords = [coord_to_string(r, c, True) for r, c in equals_positions]
        all_debug_info['eqs_on_board'] = eq_coords
        print(f"1. eqs on board: {', '.join(eq_coords) if eq_coords else 'none'}")
    
    if not equals_positions:
        # No equals signs - return empty list
        if debug:
            all_debug_info['valid_lines'] = []
            all_debug_info['error'] = "No equals signs found on board"
        return [], all_debug_info
    
    # Collect valid lines
    valid_lines = []
    valid_lines_info = []
    
    # For each equals sign, generate moves
    for eq_row, eq_col in equals_positions:
        # Get ALL paths (both horizontal and vertical)
        paths = get_valid_paths_through_equals(game.board, eq_row, eq_col)
        
        # Process each path (horizontal and/or vertical)
        for lhs_path, rhs_path, is_horizontal in paths:
            # Build level_filter_arr for LHS and RHS (for debugging)
            lhs_filter = build_level_filter_arr(lhs_path, game.board, reverse=True)
            rhs_filter = build_level_filter_arr(rhs_path, game.board, reverse=False)
            
            # Format valid lines for debug output
            if lhs_path or rhs_path:
                lhs_start = coord_to_string(lhs_path[0][0], lhs_path[0][1], is_horizontal) if lhs_path else coord_to_string(eq_row, eq_col, is_horizontal)
                lhs_end = coord_to_string(lhs_path[-1][0], lhs_path[-1][1], is_horizontal) if lhs_path else coord_to_string(eq_row, eq_col, is_horizontal)
                rhs_start = coord_to_string(rhs_path[0][0], rhs_path[0][1], is_horizontal) if rhs_path else coord_to_string(eq_row, eq_col, is_horizontal)
                rhs_end = coord_to_string(rhs_path[-1][0], rhs_path[-1][1], is_horizontal) if rhs_path else coord_to_string(eq_row, eq_col, is_horizontal)
                line_str = f"{lhs_start}-{lhs_end} -> {rhs_start}-{rhs_end}"
                valid_lines.append(line_str)
                valid_lines_info.append({
                    'line': line_str,
                    'lhs_filter': lhs_filter,
                    'rhs_filter': rhs_filter,
                    'lhs_path': lhs_path,
                    'rhs_path': rhs_path,
                    'is_horizontal': is_horizontal
                })
            
            # Generate moves for this path
            moves, debug_info = generate_moves_for_equals(
                game.board,
                game.rack,
                game.chars,
                game.bonus,
                eq_row,
                eq_col,
                lhs_path,
                rhs_path,
                is_horizontal,
                debug=debug
            )
            
            all_moves.extend(moves)
            if debug:
                key = f"eq_{eq_row}_{eq_col}_{'H' if is_horizontal else 'V'}"
                all_debug_info[key] = debug_info
    
    if debug:
        all_debug_info['valid_lines_info'] = valid_lines_info
    
    if debug:
        all_debug_info['valid_lines'] = valid_lines
        print(f"2. Valid lines: {' | '.join(valid_lines) if valid_lines else 'none'}")
        
        # Print lhs and rhs level_filter_arr for each valid line
        if valid_lines_info:
            print(f"2b. LHS and RHS level_filter_arr for each valid line:")
            for i, line_info in enumerate(valid_lines_info, 1):
                lhs_filter = line_info['lhs_filter']
                rhs_filter = line_info['rhs_filter']
                # Format the filter arrays (always 16 elements)
                lhs_str = str(lhs_filter)  # Should be exactly 16 elements
                rhs_str = str(rhs_filter)  # Should be exactly 16 elements
                print(f"   Line {i} ({line_info['line']}):")
                print(f"      LHS: {lhs_str}")
                print(f"      RHS: {rhs_str}")
        
        # Print tiles_arr per line (each line has its own tiles_arr with existing tiles)
        print(f"3. tiles_arr per line:")
        
        # Print first 10 eqs, correct_eqs, and constrained_eqs per line
        if valid_lines_info:
            for i, line_info in enumerate(valid_lines_info, 1):
                is_horizontal = line_info['is_horizontal']
                # Find the corresponding debug info for this line
                eq_row, eq_col = equals_positions[0] if equals_positions else (0, 0)
                # Try to find the debug info for this specific line
                key = f"eq_{eq_row}_{eq_col}_{'H' if is_horizontal else 'V'}"
                if key in all_debug_info:
                    debug_info = all_debug_info[key]
                else:
                    # Fallback to first available
                    for k in all_debug_info:
                        if k.startswith('eq_'):
                            debug_info = all_debug_info[k]
                            break
                    else:
                        continue
                
                print(f"   Line {i} ({line_info['line']}):")
                
                # Print tiles_arr for this line
                tiles_arr = debug_info.get('tiles_arr', [])
                rack_tiles = debug_info.get('rack_tiles', [])
                print(f"      3. tiles_arr: {tiles_arr}")
                print(f"         (rack tiles only - existing tiles are in level_filter_arr above)")
                
                # Print first 10 eqs
                first_10 = debug_info.get('first_10_eqs', [])
                print(f"      4. first 10 eqs: {first_10[:10] if first_10 else 'none'}")
                
                # Print correct_eqs
                correct_eqs = debug_info.get('correct_eqs', [])
                print(f"      5. correct_eqs: {len(correct_eqs)} total")
                if correct_eqs:
                    print(f"         First 10: {correct_eqs[:10]}")
                
                # Print constrained_eqs
                constrained = debug_info.get('constrained_eqs', [])
                print(f"      6. constrained_eqs: {len(constrained)} total")
                if constrained:
                    print(f"         First 10: {constrained[:10]}")
    
    # Sort by score (descending)
    all_moves.sort(key=lambda x: x[3], reverse=True)
    
    return all_moves, all_debug_info


def format_move_for_display(coord: str, move_str: str, leave: str, score: int) -> str:
    """Format a move for display in the gen command output."""
    # Truncate move_str and leave if too long
    move_display = move_str[:20] if len(move_str) > 20 else move_str
    leave_display = leave[:15] if len(leave) > 15 else leave
    
    return f"  {coord:<4} {move_display:<20} {leave_display:<15} {score:>5}"
