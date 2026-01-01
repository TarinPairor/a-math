"""Core game logic and state management."""

import json
import random
import re
from typing import List, Tuple, Optional
from copy import deepcopy
from tiles import resolve_tile, get_tile_by_index, get_tile_display
from ui import display_board, display_info, show_state as ui_show_state


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
        
        for identifier in identifiers:
            if 0 <= current_row < 15 and 0 <= current_col < 15:
                if identifier == '.':
                    # Skip existing tile, just move position
                    pass
                else:
                    # Resolve tile identifier to tile key
                    tile_key = self._resolve_tile(identifier)
                    if tile_key:
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

