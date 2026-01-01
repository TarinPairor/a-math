"""Core game logic and state management."""

import json
import random
import re
from typing import List, Tuple, Optional
from copy import deepcopy
from tiles import resolve_tile, get_tile_by_index, get_tile_display
from ui import display_board, display_info, show_state as ui_show_state
from validation import validate_play, BLANK_VALUES, NUMBER_TILES, is_blank_tile, get_blank_value


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
        
        # Initialize bag from chars.json
        self._initialize_bag()
    
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
    
    def _save_state(self):
        """Save current game state to history"""
        state = {
            'board': deepcopy(self.board),
            'bag': self.bag.copy(),
            'rack': self.rack.copy(),
            'turn': self.turn
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
            self.current_state_index = index
    
    def new_game(self):
        """Start a new game"""
        self.board = [[' ' for _ in range(15)] for _ in range(15)]
        self._initialize_bag()
        self.rack = self._draw_tiles(8)
        self.turn = 0
        self.history = []
        self.current_state_index = -1
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
        Place tiles on the board.
        coord: coordinate string (e.g., "8G" or "G8")
        tiles_str: Comma-separated string of tile identifiers (e.g., "1,+,12,+/-,3,=,.,.")
        Use "." to indicate existing tiles (skip position)
        Returns True if successful, False if there were errors
        """
        # Save current state for rollback if needed
        if self.current_state_index < len(self.history) - 1:
            # Not at latest state, restore to latest first
            self._restore_state(len(self.history) - 1)
        
        # Save board state before making changes
        original_board = [row[:] for row in self.board]
        original_turn = self.turn
        
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
                elif identifier.startswith('(') and identifier.endswith(')'):
                    # Blank tile with value: (value) format
                    blank_value = identifier[1:-1]  # Remove parentheses
                    
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
                                if prev_id != '.' and not (prev_id.startswith('(') and prev_id.endswith(')')):
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
                                if next_id != '.' and not (next_id.startswith('(') and next_id.endswith(')')):
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
                        # Resolve compound tiles and blank tiles for display
                        resolved_tiles = []
                        for _, _, tile in sequence:
                            if tile in ['×/÷', '+/-']:
                                # Show both possibilities for compound tiles
                                if tile == '+/-':
                                    resolved_tiles.append('+/-')
                                else:
                                    resolved_tiles.append('×/÷')
                            elif is_blank_tile(tile):
                                # Show blank tile value
                                blank_value = get_blank_value(tile)
                                resolved_tiles.append(blank_value)
                            else:
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
                        # Resolve compound tiles and blank tiles for display
                        resolved_tiles = []
                        for _, _, tile in sequence:
                            if tile in ['×/÷', '+/-']:
                                # Show both possibilities for compound tiles
                                if tile == '+/-':
                                    resolved_tiles.append('+/-')
                                else:
                                    resolved_tiles.append('×/÷')
                            elif is_blank_tile(tile):
                                # Show blank tile value
                                blank_value = get_blank_value(tile)
                                resolved_tiles.append(blank_value)
                            else:
                                resolved_tiles.append(tile)
                        tiles_str = ' '.join(resolved_tiles)
                        print(f"  {direction}: {tiles_str}")
        
        # Success - advance turn and save state
        self.turn += 1
        self._save_state()
        return True
    
    def get_tile(self, coord: str) -> Optional[str]:
        """Get tile at coordinate"""
        row, col, _ = self._parse_coord(coord)
        if 0 <= row < 15 and 0 <= col < 15:
            tile = self.board[row][col]
            return tile if tile != ' ' else None
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
        
        # Ensure bag is initialized
        if not self.bag:
            self._initialize_bag()
        
        # Check if there are enough tiles in the bag
        if len(self.bag) < 8:
            print(f"Error: Not enough tiles in bag. Bag has {len(self.bag)} tiles, need 8.")
            return False
        
        # Randomly sample 8 tiles from the bag without removing them
        self.rack = random.sample(self.bag, 8)
        
        # Save state
        self._save_state()
        return True
    
    def display_board(self):
        """Display the game board"""
        display_board(self.chars, self.board)
    
    def display_info(self):
        """Display game information"""
        display_info(self.chars, self.bag, self.rack, self.turn)
    
    def show_state(self):
        """Show current game state"""
        ui_show_state(self.chars, self.board, self.bag, self.rack, self.turn)
    
    def next_play(self):
        """Go to next play in history"""
        if self.current_state_index < len(self.history) - 1:
            self._restore_state(self.current_state_index + 1)
            return True
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

