"""Core game logic and state management."""

import json
import random
import re
from typing import List, Tuple, Optional
from copy import deepcopy
from tiles import resolve_tile, get_tile_by_index, get_tile_display
from ui import display_board, display_info, show_state as ui_show_state
from validation import validate_play, BLANK_VALUES, NUMBER_TILES, is_blank_tile, get_blank_value
from scoring import calculate_play_score, load_bonus_squares


class AMathGame:
    def __init__(self, chars_file: str = "chars.json"):
        with open(chars_file, 'r') as f:
            self.chars = json.load(f)
        
        self.board = [[' ' for _ in range(15)] for _ in range(15)]
        self.bag = []
        self.rack = []
        self.turn = 0
        self.history = []  # List of game states for navigation
        self.current_state_index = -1
        self.scores = [0, 0]  # Scores for player 0 and player 1
        self.player_names = ["euclid", "pythagoras"]  # Default player names
        
        # Initialize bag from chars.json
        self._initialize_bag()
        
        # Load bonus squares
        self.bonus = load_bonus_squares("bonus.json")
    
    def _initialize_bag(self):
        """Initialize the bag with all tiles from chars.json"""
        self.bag = []
        for char_key, char_data in self.chars.items():
            count = char_data['count']
            for _ in range(count):
                self.bag.append(char_key)
        random.shuffle(self.bag)
    
    def _draw_tiles(self, count: int) -> List[str]:
        """Draw count tiles from bag"""
        drawn = []
        for _ in range(min(count, len(self.bag))):
            drawn.append(self.bag.pop())
        return drawn
    
    def _get_tiles_on_board(self) -> List[str]:
        """Get all tiles currently on the board (base tiles only, not resolved values)"""
        tiles = []
        for row in self.board:
            for tile in row:
                if tile != ' ':
                    # Extract base tile from compound/blank tiles
                    if tile.startswith('?'):
                        # Blank tile - count as the blank tile itself
                        tiles.append('?')
                    elif ':' in tile and tile.split(':', 1)[0] in ['×/÷', '+/-']:
                        # Compound tile - count as the compound tile itself
                        compound_tile = tile.split(':', 1)[0]
                        tiles.append(compound_tile)
                    else:
                        tiles.append(tile)
        return tiles
    
    def _remove_tiles_from_bag(self, tiles_to_remove: List[str]):
        """
        Remove specific tiles from the bag (set subtraction).
        Removes all occurrences of each tile in the list.
        """
        for tile in tiles_to_remove:
            if tile in self.bag:
                self.bag.remove(tile)
    
    def _get_bag_unseen_count(self) -> int:
        """
        Calculate bag+unseen tiles count.
        Bag+unseen = Total tiles (100) - tiles on board - tiles on current rack
        """
        total_tiles = sum(char_data['count'] for char_data in self.chars.values())
        tiles_on_board = len(self._get_tiles_on_board())
        tiles_on_rack = len(self.rack)
        return total_tiles - tiles_on_board - tiles_on_rack
    
    def _save_state(self):
        """Save current game state to history"""
        state = {
            'board': deepcopy(self.board),
            'bag': self.bag.copy(),
            'rack': self.rack.copy(),
            'turn': self.turn,
            'scores': self.scores.copy()
        }
        # Remove future states if we're not at the end
        if self.current_state_index < len(self.history) - 1:
            self.history = self.history[:self.current_state_index + 1]
        self.history.append(state)
        self.current_state_index = len(self.history) - 1
    
    def _restore_state(self, index: int):
        """Restore game state from history"""
        if 0 <= index < len(self.history):
            state = self.history[index]
            self.board = deepcopy(state['board'])
            self.bag = state['bag'].copy()
            self.rack = state['rack'].copy()
            self.turn = state['turn']
            self.scores = state.get('scores', [0, 0]).copy()
            self.current_state_index = index
    
    def new_game(self):
        """Start a new game"""
        self.board = [[' ' for _ in range(15)] for _ in range(15)]
        self._initialize_bag()
        self.rack = self._draw_tiles(8)
        self.turn = 0
        self.history = []
        self.current_state_index = -1
        self.scores = [0, 0]  # Reset scores
        # NOTE: After drawing rack, bag now has 100 - 8 = 92 tiles
        self._save_state()
    
    def _parse_coord(self, coord: str) -> Tuple[int, int, bool]:
        """
        Parse coordinate string.
        Returns (row, col, is_horizontal)
        Format: letter+number for vertical, number+letter for horizontal
        e.g., "8G" = row 7, col 6, vertical
        e.g., "G8" = row 7, col 6, horizontal
        """
        coord = coord.upper().strip()
        
        # Check if it's number+letter (horizontal) or letter+number (vertical)
        match = re.match(r'([A-O])(\d+)', coord)
        if match:
            # Letter first = vertical
            letter = match.group(1)
            number = int(match.group(2))
            col = ord(letter) - ord('A')
            row = number - 1
            return row, col, False
        
        match = re.match(r'(\d+)([A-O])', coord)
        if match:
            # Number first = horizontal
            number = int(match.group(1))
            letter = match.group(2)
            row = number - 1
            col = ord(letter) - ord('A')
            return row, col, True
        
        raise ValueError(f"Invalid coordinate format: {coord}")
    
    
    def _parse_play_string(self, play: str) -> List[Optional[str]]:
        """
        Parse play string into list of tile keys.
        Returns list where None means '.' (existing tile), str means tile key to place.
        Handles multi-character keys like "10", "11", etc.
        """
        result = []
        i = 0
        play_len = len(play)
        
        # Sort keys by length (longest first) to match multi-char keys first
        sorted_keys = sorted(self.chars.keys(), key=len, reverse=True)
        
        while i < play_len:
            if play[i] == '.':
                result.append(None)  # Existing tile
                i += 1
            else:
                # Try to match longest possible key
                matched = False
                for key in sorted_keys:
                    if play[i:].startswith(key):
                        result.append(key)
                        i += len(key)
                        matched = True
                        break
                
                if not matched:
                    # Single character match
                    result.append(play[i])
                    i += 1
        
        return result
    
    def commit(self, coord: str, tiles_str: str) -> bool:
        """
        Place tiles on the board, exchange tiles, or pass turn.
        coord: coordinate string (e.g., "8G" or "G8"), or "exch"/"exchange" for exchange, or "pass" for pass
        tiles_str: Comma-separated string of tile identifiers (e.g., "1,+,12,+/-,3,=,.,.")
                   For exchange: tiles to exchange (e.g., "12,?,*/,*,=,/")
                   For pass: ignored
        Use "." to indicate existing tiles (skip position)
        Use "?value" to indicate blank tiles (e.g., "?0", "?5", "?+")
        Returns True if successful, False if there were errors
        """
        # NOTE: If we're not at the latest state, we're making a new commit from a previous state
        # This should truncate all future states (like git history)
        if self.current_state_index < len(self.history) - 1:
            # Truncate all states after the current one
            self.history = self.history[:self.current_state_index + 1]
            # We're already at the state we want, no need to restore
        
        # Save board state before making changes
        original_board = [row[:] for row in self.board]
        original_turn = self.turn
        original_rack = self.rack.copy()  # Save original rack to track kept tiles
        
        # Handle special commit types: exchange and pass
        coord_lower = coord.lower().strip()
        if coord_lower in ['exch', 'exchange']:
            return self._commit_exchange(tiles_str, original_rack)
        elif coord_lower == 'pass':
            return self._commit_pass(original_rack)
        
        # Normal commit - parse coordinate
        try:
            row, col, is_horizontal = self._parse_coord(coord)
        except ValueError as e:
            print(f"Error: {e}")
            return False
        
        # Parse comma-separated tiles
        identifiers = [id_str.strip() for id_str in tiles_str.split(',')]
        current_row, current_col = row, col
        new_tiles = []  # Track newly placed tiles for validation
        
        # NOTE: Check for out of bounds BEFORE placing any tiles
        # Count how many positions we need (including skips, as they still take up space)
        num_positions = len(identifiers)
        if is_horizontal:
            if current_col + num_positions > 15:
                print(f"Error: Play extends beyond board boundary. Starting at column {chr(ord('A')+current_col)}{current_row+1}, {num_positions} positions would extend to column {chr(ord('A')+current_col+num_positions-1)} (board only has columns A-O)")
                return False
        else:
            if current_row + num_positions > 15:
                print(f"Error: Play extends beyond board boundary. Starting at {chr(ord('A')+current_col)}{current_row+1}, {num_positions} positions would extend to row {current_row+num_positions} (board only has rows 1-15)")
                return False
        
        # NOTE: Check tile count limit (8 tiles maximum per turn) Remove this to play around with cases
        # Count non-skip identifiers (excluding '.' for skipping existing tiles)
        num_tiles_to_place = len([id for id in identifiers if id != '.'])
        if num_tiles_to_place > 8:
            print(f"Error: Cannot place more than 8 tiles in one turn. Attempted to place {num_tiles_to_place} tiles.")
            return False
        
        for identifier in identifiers:
            if 0 <= current_row < 15 and 0 <= current_col < 15:
                if identifier == '.':
                    # Skip existing tile, just move position
                    # NOTE: Verify that there IS an existing tile to skip
                    if original_board[current_row][current_col] == ' ':
                        print(f"Error: Cannot skip empty position at {chr(ord('A')+current_col)}{current_row+1}")
                        self.board = original_board
                        self.turn = original_turn
                        return False
                    # Just move to next position without placing anything
                    pass
                elif identifier.startswith('?'):
                    # Blank tile with value: ?value format
                    blank_value = identifier[1:]  # Remove '?' prefix
                    
                    # Validate blank value: must be a valid single value (0-20, +, -, ×, ÷, =)
                    # First try to resolve as alias (e.g., "/" -> "÷", "*" -> "×")
                    resolved_value = None
                    if blank_value in self.chars:
                        # Direct tile key
                        resolved_value = blank_value
                    else:
                        # Try to resolve as alias
                        for char_key, char_data in self.chars.items():
                            if char_data.get('alias') == blank_value:
                                resolved_value = char_key
                                break
                    
                    # Check if resolved value is valid for blank tiles
                    if resolved_value is None or resolved_value not in BLANK_VALUES:
                        # Invalid blank value - restore board and return False
                        print(f"Error: Invalid blank tile value '{blank_value}'. Blank tiles can only represent: 0-20, +, -, ×, ÷, =")
                        self.board = original_board
                        self.turn = original_turn
                        return False
                    
                    # NOTE: Check that we're not overlapping with existing tiles (except when using '.')
                    if original_board[current_row][current_col] != ' ':
                        # Trying to place a tile where one already exists
                        print(f"Error: Cannot place tile at {chr(ord('A')+current_col)}{current_row+1}: position already occupied")
                        self.board = original_board
                        self.turn = original_turn
                        return False
                    
                    # Store blank tile as "?value" to track what it represents
                    # Only add to new_tiles if this position was empty in original board
                    if original_board[current_row][current_col] == ' ':
                        new_tiles.append((current_row, current_col, f"?{resolved_value}"))
                    self.board[current_row][current_col] = f"?{resolved_value}"
                elif '?' in identifier and not identifier.startswith('?'):
                    # Compound tile with declared value: format is "compound?resolved" or "index?index"
                    # Examples: "+/?+", "+/?-", "*/?*", "*/?/", or "23?21"
                    parts = identifier.split('?', 1)
                    if len(parts) != 2:
                        print(f"Error: Invalid compound tile declaration format '{identifier}'. Use format like '+/?+' or '23?21'")
                        self.board = original_board
                        self.turn = original_turn
                        return False
                    
                    compound_part = parts[0].strip()
                    resolved_part = parts[1].strip()
                    
                    # Resolve the compound tile
                    compound_tile = None
                    if compound_part in ['+/-', '+/', '×/÷', '*/']:
                        # Direct compound tile or alias
                        if compound_part == '+/':
                            compound_tile = '+/-'
                        elif compound_part == '*/':
                            compound_tile = '×/÷'
                        else:
                            compound_tile = compound_part
                    else:
                        # Try as index
                        try:
                            compound_index = int(compound_part)
                            compound_tile = get_tile_by_index(self.chars, compound_index)
                            if compound_tile not in ['+/-', '×/÷']:
                                compound_tile = None
                        except ValueError:
                            pass
                    
                    if compound_tile is None:
                        print(f"Error: Could not resolve compound tile from '{compound_part}'. Use '+/-', '+/', '×/÷', '*/', or the tile index.")
                        self.board = original_board
                        self.turn = original_turn
                        return False
                    
                    # Resolve the declared value
                    resolved_value = None
                    if resolved_part in ['+', '-', '×', '÷']:
                        # Direct operator
                        resolved_value = resolved_part
                    elif resolved_part in ['*', '/']:
                        # Alias
                        if resolved_part == '*':
                            resolved_value = '×'
                        else:
                            resolved_value = '÷'
                    else:
                        # Try as index
                        try:
                            resolved_index = int(resolved_part)
                            resolved_tile = get_tile_by_index(self.chars, resolved_index)
                            if resolved_tile in ['+', '-', '×', '÷']:
                                resolved_value = resolved_tile
                        except ValueError:
                            pass
                    
                    if resolved_value is None:
                        print(f"Error: Could not resolve declared value '{resolved_part}'. Must be '+', '-', '×', '÷', '*', '/', or the operator's index.")
                        self.board = original_board
                        self.turn = original_turn
                        return False
                    
                    # Validate that the resolved value is valid for this compound tile
                    if compound_tile == '+/-' and resolved_value not in ['+', '-']:
                        print(f"Error: '+/-' can only be resolved to '+' or '-', not '{resolved_value}'")
                        self.board = original_board
                        self.turn = original_turn
                        return False
                    if compound_tile == '×/÷' and resolved_value not in ['×', '÷']:
                        print(f"Error: '×/÷' can only be resolved to '×' or '÷', not '{resolved_value}'")
                        self.board = original_board
                        self.turn = original_turn
                        return False
                    
                    # NOTE: Check that we're not overlapping with existing tiles
                    if original_board[current_row][current_col] != ' ':
                        print(f"Error: Cannot place tile at {chr(ord('A')+current_col)}{current_row+1}: position already occupied")
                        self.board = original_board
                        self.turn = original_turn
                        return False
                    
                    # Store compound tile with declared value: "compound:resolved" format
                    # Only add to new_tiles if this position was empty in original board
                    # Store the compound tile with declared value in new_tiles for validation
                    if original_board[current_row][current_col] == ' ':
                        new_tiles.append((current_row, current_col, f"{compound_tile}:{resolved_value}"))
                    # Store as "compound:resolved" on the board to track the declared value
                    self.board[current_row][current_col] = f"{compound_tile}:{resolved_value}"
                else:
                    # Resolve tile identifier to tile key
                    tile_key = self._resolve_tile(identifier)
                    if tile_key:
                        # NOTE: Validate that multi-digit number tiles (10-20) are not used
                        # adjacent to other number tiles - must use single digits to form numbers
                        if tile_key in NUMBER_TILES and len(tile_key) > 1:
                            current_idx = identifiers.index(identifier)
                            
                            # Check if previous identifier is also a number tile
                            if current_idx > 0:
                                prev_id = identifiers[current_idx - 1].strip()
                                if prev_id != '.' and not prev_id.startswith('?'):
                                    prev_tile = self._resolve_tile(prev_id)
                                    # if prev_tile and prev_tile in NUMBER_TILES:
                                    #     # Invalid: number tile followed by multi-digit tile
                                    #     print(f"Error: Multi-digit number tile '{tile_key}' cannot be used adjacent to number tiles. Use single digits separated by commas (e.g., '1,7,2' instead of '2,17' or '17,2')")
                                    #     self.board = original_board
                                    #     self.turn = original_turn
                                    #     return False
                            
                            # Check if next identifier is also a number tile
                            if current_idx + 1 < len(identifiers):
                                next_id = identifiers[current_idx + 1].strip()
                                if next_id != '.' and not next_id.startswith('?'):
                                    next_tile = self._resolve_tile(next_id)
                                    # if next_tile and next_tile in NUMBER_TILES:
                                    #     # Invalid: multi-digit tile followed by number tile
                                    #     print(f"Error: Multi-digit number tile '{tile_key}' cannot be used adjacent to number tiles. Use single digits separated by commas (e.g., '1,7,2' instead of '17,2' or '2,17')")
                                    #     self.board = original_board
                                    #     self.turn = original_turn
                                    #     return False
                        
                        # NOTE: Check that we're not overlapping with existing tiles (except when using '.')
                        if original_board[current_row][current_col] != ' ':
                            # Trying to place a tile where one already exists
                            print(f"Error: Cannot place tile at {chr(ord('A')+current_col)}{current_row+1}: position already occupied")
                            self.board = original_board
                            self.turn = original_turn
                            return False
                        
                        # Only add to new_tiles if this position was empty in original board
                        if original_board[current_row][current_col] == ' ':
                            new_tiles.append((current_row, current_col, tile_key))
                        # Place the tile directly (no rack checking)
                        # For compound tiles, we'll lock in the resolved value after validation
                        self.board[current_row][current_col] = tile_key
                    else:
                        # Error - restore board and return False
                        print(f"Warning: Could not resolve tile identifier '{identifier}', skipping")
                        self.board = original_board
                        self.turn = original_turn
                        return False
                
                # Move to next position
                if is_horizontal:
                    current_col += 1
                else:
                    current_row += 1
            else:
                break
        
        # Validate the play (use original board for validation, not the modified one)
        if new_tiles:
            is_valid, error_message, parsed_equations = validate_play(
                original_board, new_tiles, self.turn, self.chars, is_horizontal, debug=True
            )
            if not is_valid:
                # Invalid play - restore board and return False
                print(f"Invalid play: {error_message}")
                # Display parsed equations for debugging
                if parsed_equations:
                    print("\nParsed equations:")
                    for direction, sequence in parsed_equations:
                        # Show resolved values (locked compound tiles show their locked value)
                        resolved_tiles = []
                        for _, _, tile in sequence:
                            if is_blank_tile(tile):
                                # Show blank tile value
                                blank_value = get_blank_value(tile)
                                resolved_tiles.append(blank_value)
                            else:
                                # For locked compound tiles, show the locked value
                                # For regular tiles, show as-is
                                resolved_tiles.append(tile)
                        tiles_str = ' '.join(resolved_tiles)
                        print(f"  {direction}: {tiles_str}")
                self.board = original_board
                self.turn = original_turn
                return False
            else:
                # Display parsed equations for debugging (even on success)
                if parsed_equations:
                    print("\nParsed equations:")
                    for direction, sequence in parsed_equations:
                        # Show resolved values (locked compound tiles show their locked value)
                        resolved_tiles = []
                        for _, _, tile in sequence:
                            if is_blank_tile(tile):
                                # Show blank tile value
                                blank_value = get_blank_value(tile)
                                resolved_tiles.append(blank_value)
                            else:
                                # For locked compound tiles, show the locked value
                                # For regular tiles, show as-is
                                resolved_tiles.append(tile)
                        tiles_str = ' '.join(resolved_tiles)
                        print(f"  {direction}: {tiles_str}")
                
                # NOTE: Lock in resolved values for compound tiles that were just placed
                # Find the resolved sequence from parsed_equations and lock in compound tile values
                if parsed_equations:
                    # Get the first valid resolved sequence (from the play direction equation)
                    resolved_sequence = None
                    for direction, sequence in parsed_equations:
                        # Prefer the play direction equation
                        if (is_horizontal and 'horizontal' in direction) or (not is_horizontal and 'vertical' in direction):
                            resolved_sequence = sequence
                            break
                    # If not found, use the first one
                    if not resolved_sequence and parsed_equations:
                        resolved_sequence = parsed_equations[0][1]
                    
                    # Lock in compound tile values
                    if resolved_sequence:
                        for r, c, resolved_tile in resolved_sequence:
                            # Check if this position has a compound tile that was just placed
                            if (r, c) in [(nr, nc) for nr, nc, _ in new_tiles]:
                                board_tile = self.board[r][c]
                                if board_tile in ['×/÷', '+/-']:
                                    # This is a new compound tile - lock in the resolved value
                                    # Store as "symbol:resolved" format
                                    self.board[r][c] = f"{board_tile}:{resolved_tile}"
                
                # NOTE: Calculate score for this play
                # Score is the sum of all equations formed (horizontal and vertical)
                play_score = 0
                if parsed_equations:
                    new_positions = {(r, c) for r, c, _ in new_tiles}
                    for direction, sequence in parsed_equations:
                        # Only score equations (sequences with equals signs)
                        has_equals = any(
                            tile == '=' or (is_blank_tile(tile) and get_blank_value(tile) == '=')
                            for _, _, tile in sequence
                        )
                        if has_equals and len(sequence) > 1:
                            # Extract tiles from board (use actual board tiles, not resolved values for scoring)
                            equation_tiles = []
                            for r, c, _ in sequence:
                                # Get the actual tile from the board
                                board_tile = self.board[r][c]
                                equation_tiles.append((r, c, board_tile))
                            
                            # Calculate score for this equation
                            try:
                                eq_score = calculate_play_score(new_tiles, equation_tiles, self.chars, self.bonus)
                                play_score += eq_score
                            except Exception as e:
                                # If scoring fails, just continue (shouldn't happen for valid plays)
                                pass
                
                # Add score to current player (turn % 2 gives player index)
                player_index = (self.turn) % 2
                self.scores[player_index] += play_score
                
                # NOTE: Remove placed tiles from bag
                # Extract base tiles from new_tiles (handle compound/blank tiles)
                placed_tiles = []
                for r, c, tile in new_tiles:
                    if tile.startswith('?'):
                        # Blank tile
                        placed_tiles.append('?')
                    elif ':' in tile and tile.split(':', 1)[0] in ['×/÷', '+/-']:
                        # Compound tile - use the base compound tile
                        compound_tile = tile.split(':', 1)[0]
                        placed_tiles.append(compound_tile)
                    else:
                        placed_tiles.append(tile)
                
                self._remove_tiles_from_bag(placed_tiles)
                
                # NOTE: Draw new rack for next player (from bag, without considering kept tiles)
                # Special case: If bag has < 16 tiles (8 + 8) and a play would leave < 8 tiles,
                # we stop drawing. Check if bag will have < 8 tiles after this play.
                tiles_remaining_after_play = len(self.bag)
                if tiles_remaining_after_play >= 8:
                    # Draw 8 tiles for next player
                    new_rack = self._draw_tiles(8)
                    self.rack = new_rack
                else:
                    # Not enough tiles - draw what's available (or nothing)
                    if tiles_remaining_after_play > 0:
                        new_rack = self._draw_tiles(tiles_remaining_after_play)
                        self.rack = new_rack
                    else:
                        # Bag is empty
                        self.rack = []
        
        # Success - advance turn and save state
        # NOTE: Exchange scores 0 points
        self.turn += 1
        self._save_state()
        return True
    
    def _commit_exchange(self, tiles_str: str, original_rack: List[str]) -> bool:
        """
        Exchange tiles from the rack.
        tiles_str: Comma-separated string of tile identifiers to exchange (e.g., "12,?,*/,*,=,/")
        Returns True if successful, False if there were errors
        """
        # NOTE: If we're not at the latest state, we're making a new commit from a previous state
        # This should truncate all future states (like git history)
        if self.current_state_index < len(self.history) - 1:
            # Truncate all states after the current one
            self.history = self.history[:self.current_state_index + 1]
        
        # Parse comma-separated tiles
        identifiers = [id_str.strip() for id_str in tiles_str.split(',')]
        
        if not identifiers:
            print("Error: No tiles specified for exchange")
            return False
        
        # Resolve all identifiers to tile keys
        exchange_tiles = []
        for identifier in identifiers:
            tile = self._resolve_tile(identifier)
            if tile:
                exchange_tiles.append(tile)
            else:
                print(f"Error: Could not resolve tile identifier '{identifier}'")
                return False
        
        # Validate that all exchange tiles are on the current rack
        rack_copy = original_rack.copy()
        for tile in exchange_tiles:
            if tile in rack_copy:
                rack_copy.remove(tile)
            else:
                print(f"Error: Tile '{tile}' is not on the current rack. Rack: {original_rack}")
                return False
        
        # Calculate kept tiles (tiles NOT being exchanged)
        kept_tiles = rack_copy  # Remaining tiles after removing exchange tiles
        
        # Put exchange tiles back in the bag
        for tile in exchange_tiles:
            self.bag.append(tile)
        random.shuffle(self.bag)  # Shuffle after adding tiles back
        
        # Draw new tiles for the current player (same number as exchanged)
        num_to_exchange = len(exchange_tiles)
        if len(self.bag) >= num_to_exchange:
            new_tiles = self._draw_tiles(num_to_exchange)
            # Update rack: kept tiles + new tiles
            self.rack = kept_tiles + new_tiles
        else:
            # Not enough tiles in bag - draw what's available
            if len(self.bag) > 0:
                new_tiles = self._draw_tiles(len(self.bag))
                self.rack = kept_tiles + new_tiles
            else:
                # Bag is empty - just keep the kept tiles
                self.rack = kept_tiles
        
        # Success - advance turn and save state
        self.turn += 1
        self._save_state()
        return True
    
    def _commit_pass(self, original_rack: List[str]) -> bool:
        """
        Pass the turn (all 8 tiles are kept).
        Returns True if successful, False if there were errors
        """
        # NOTE: If we're not at the latest state, we're making a new commit from a previous state
        # This should truncate all future states (like git history)
        if self.current_state_index < len(self.history) - 1:
            # Truncate all states after the current one
            self.history = self.history[:self.current_state_index + 1]
        
        # Rack stays the same (all tiles kept)
        self.rack = original_rack
        
        # Success - advance turn and save state
        # NOTE: Pass scores 0 points
        self.turn += 1
        self._save_state()
        return True
    
    def get_tile(self, coord: str) -> Optional[str]:
        """Get tile at coordinate. For locked compound tiles, returns the compound symbol."""
        row, col, _ = self._parse_coord(coord)
        if 0 <= row < 15 and 0 <= col < 15:
            tile = self.board[row][col]
            if tile == ' ':
                return None
            # If it's a locked compound tile, return just the compound symbol
            if ':' in tile:
                parts = tile.split(':', 1)
                if len(parts) == 2 and parts[0] in ['×/÷', '+/-']:
                    return parts[0]  # Return the compound symbol
            return tile
        return None
    
    def _resolve_tile(self, identifier: str) -> Optional[str]:
        """Resolve a tile identifier using the tiles module"""
        return resolve_tile(self.chars, identifier)
    
    def set_rack(self, tiles_str: str) -> bool:
        """
        Set the current player's rack from comma-separated tile identifiers.
        tiles_str: Comma-separated string of indices or aliases (e.g., "0,1,2,3,4,5,6,7" or "0,+,*,/,=,?")
        Must provide exactly 8 tiles.
        Returns True if successful, False if there were errors
        """
        if self.current_state_index < len(self.history) - 1:
            # Not at latest state, restore to latest first
            self._restore_state(len(self.history) - 1)
        
        # Save old rack before changing
        old_rack = self.rack.copy()
        
        new_rack = []
        identifiers = [id_str.strip() for id_str in tiles_str.split(',')]
        
        # Check that exactly 8 tiles are provided
        if len(identifiers) != 8:
            print(f"Error: Rack must have exactly 8 tiles. Provided {len(identifiers)} tiles.")
            return False
        
        for identifier in identifiers:
            tile = self._resolve_tile(identifier)
            if tile:
                new_rack.append(tile)
            else:
                print(f"Error: Could not resolve tile identifier '{identifier}'")
                return False
        
        # Verify we have exactly 8 tiles
        if len(new_rack) != 8:
            print(f"Error: Could not create rack with 8 tiles. Only found {len(new_rack)} valid tiles.")
            return False
        
        # NOTE: Put old rack tiles back in the bag
        for tile in old_rack:
            self.bag.append(tile)
        random.shuffle(self.bag)  # Shuffle after adding tiles back
        
        # NOTE: Remove new rack tiles from bag (set subtraction)
        self._remove_tiles_from_bag(new_rack)
        
        self.rack = new_rack
        
        # Save state
        self._save_state()
        return True
    
    def set_rack_random(self) -> bool:
        """
        Randomize the rack by drawing 8 tiles from the bag.
        Returns True if successful, False if there were errors (e.g., not enough tiles in bag)
        """
        if self.current_state_index < len(self.history) - 1:
            # Not at latest state, restore to latest first
            self._restore_state(len(self.history) - 1)
        
        # Save old rack before changing
        old_rack = self.rack.copy()
        
        # Ensure bag is initialized
        if not self.bag:
            self._initialize_bag()
        
        # NOTE: Put old rack tiles back in the bag
        for tile in old_rack:
            self.bag.append(tile)
        random.shuffle(self.bag)  # Shuffle after adding tiles back
        
        # Check if there are enough tiles in the bag
        if len(self.bag) < 8:
            print(f"Error: Not enough tiles in bag. Bag has {len(self.bag)} tiles, need 8.")
            return False
        
        # Randomly sample 8 tiles from the bag and remove them
        new_rack = random.sample(self.bag, 8)
        # Remove the sampled tiles from the bag
        for tile in new_rack:
            self.bag.remove(tile)
        
        self.rack = new_rack
        
        # Save state
        self._save_state()
        return True
    
    def display_board(self):
        """Display the game board"""
        display_board(self.chars, self.board)
    
    def display_info(self):
        """Display game information"""
        bag_unseen_count = self._get_bag_unseen_count()
        display_info(self.chars, self.bag, self.rack, self.turn, bag_unseen_count)
    
    def show_state(self):
        """Show current game state with correct bag+unseen count"""
        bag_unseen_count = self._get_bag_unseen_count()
        ui_show_state(self.chars, self.board, self.bag, self.rack, self.turn, bag_unseen_count, self.scores, self.player_names)
    
    def next_play(self):
        """Go to next play in history"""
        if self.current_state_index < len(self.history) - 1:
            self._restore_state(self.current_state_index + 1)
            return True
        else:
            print("Already at latest state")
        return False
    
    def previous_play(self):
        """Go to previous play in history"""
        if self.current_state_index > 0:
            self._restore_state(self.current_state_index - 1)
            return True
        return False
    
    def go_to_turn(self, turn_num: int):
        """Go to specific turn number"""
        # Find state with this turn number
        for i, state in enumerate(self.history):
            if state['turn'] == turn_num:
                self._restore_state(i)
                return True
        return False


# For backwards compatibility - allow running game.py directly
if __name__ == "__main__":
    from commands import main
    main()

