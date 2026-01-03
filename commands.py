"""Command processing and CLI interface."""

from game import AMathGame
from ui import show_state
from tiles import get_tile_display, resolve_tile
from generator import generate_moves
from typing import List


def calculate_leave(rack: List[str], move_str: str) -> str:
    """
    Calculate which tiles from the rack are left over after a move.
    
    Args:
        rack: Original rack tiles
        move_str: Move string like "12,×,(6),=,3,(+,-),6,9" where "." means existing tile
    
    Returns:
        String of tiles left in rack (space-separated), with compound tiles shown as "(+,-)" or "(×,÷)"
    """
    # Parse move string to get tiles used - handle compound tiles with commas inside parentheses
    used_tiles = []
    i = 0
    parts = move_str.split(',')
    
    while i < len(parts):
        tile = parts[i].strip()
        if tile == '.':
            i += 1
            continue  # Existing tile on board, not from rack
        
        # Check if this is part of a compound tile like "(+,-)" that was split
        if tile.startswith('(') and not tile.endswith(')'):
            # Compound tile like "(+,-)" - need to combine with next part
            if i + 1 < len(parts):
                next_part = parts[i + 1].strip()
                if next_part.endswith(')'):
                    # Combine: "(+" + "-)" = "(+,-)"
                    tile = tile + ',' + next_part
                    i += 2  # Skip both parts
                else:
                    # Malformed, just use current part
                    i += 1
            else:
                # No next part, just use current
                i += 1
        else:
            i += 1
        
        # Now process the tile (which may be combined)
        if tile.startswith('(') and tile.endswith(')'):
            tile_content = tile[1:-1]  # Remove parentheses
            if ',' in tile_content:
                # Old compound tile format like "(+,-)" or "(×,÷)" - convert to +/- or ×/÷
                if '+,-' in tile_content or '+, -' in tile_content:
                    used_tiles.append('+/-')
                elif '×,÷' in tile_content or '×, ÷' in tile_content:
                    used_tiles.append('×/÷')
                else:
                    # Regular blank tile - represented as "?" in rack
                    used_tiles.append('?')
            else:
                # Blank tile - represented as "?" in rack
                used_tiles.append('?')
        elif tile in ['+/-', '×/÷']:
            # Compound tile in new format
            used_tiles.append(tile)
        else:
            # Regular tile - use as-is
            used_tiles.append(tile)
    
    # Count tiles used
    rack_copy = rack.copy()
    for used_tile in used_tiles:
        if used_tile in rack_copy:
            rack_copy.remove(used_tile)
    
    # Format leave with compound tiles shown properly (use +/- or ×/÷ format)
    formatted_leave = []
    for tile in rack_copy:
        # Keep compound tiles as-is (they're already in the correct format)
        formatted_leave.append(tile)
    
    # Return as comma-separated string (same format as move)
    return ','.join(formatted_leave) if formatted_leave else ''


def process_command(game: AMathGame, command: str) -> bool:
    """
    Process a command and return True if should continue, False if should exit.
    """
    if not command:
        return True
    
    parts = command.split()
    cmd = parts[0].lower()
    
    if cmd == 'quit' or cmd == 'exit':
        return False
    elif cmd == 'new':
        game.new_game()
        game.show_state()
    elif cmd == 'commit':
        if len(parts) < 2:
            print("Usage: commit <coord> <tiles>")
            print("       commit exch <tiles> or commit exchange <tiles>")
            print("       commit pass")
            print("Example: commit 8G 1,+,12,+/-,3,=,.,.")
            print("         commit exch 12,?,*/,*,=,/")
            print("         commit pass")
            return True
        coord = parts[1]
        # Join all parts after coord to handle comma-separated tiles
        tiles_str = ' '.join(parts[2:]) if len(parts) > 2 else ''
        if game.commit(coord, tiles_str):
            game.show_state()
    elif cmd == 'n':
        if game.next_play():
            game.show_state()
        else:
            print("Already at latest state")
    elif cmd == 'p':
        if game.previous_play():
            game.show_state()
        else:
            print("Already at earliest state")
    elif cmd == 'turn':
        if len(parts) < 2:
            print("Usage: turn <n>")
            return True
        try:
            turn_num = int(parts[1])
            if game.go_to_turn(turn_num):
                game.show_state()
            else:
                print(f"Turn {turn_num} not found in history")
        except ValueError:
            print("Invalid turn number")
    elif cmd == 's':
        game.show_state()
    elif cmd == 'get':
        if len(parts) < 2:
            print("Usage: get <coord>")
            return True
        coord = parts[1]
        tile = game.get_tile(coord)
        if tile:
            display = get_tile_display(game.chars, tile)
            print(f"Tile at {coord}: {display} ({tile})")
        else:
            print(f"No tile at {coord}")
    elif cmd == 'rack':
        if len(parts) < 2:
            print("Usage: rack <tiles> or rack --random")
            print("Example: rack 0,1,2,3,4,5,6,7 or rack 0,+,*,/,=,?,21,22")
            print("         rack --random (randomizes rack from bag)")
            print("(must provide exactly 8 tiles - can use indices or aliases)")
            return True
        
        # Check for --random flag
        if parts[1] == '--random':
            if game.set_rack_random():
                game.show_state()
        else:
            # Join all parts after 'rack' to handle comma-separated tiles
            tiles_str = ' '.join(parts[1:])
            if game.set_rack(tiles_str):
                game.show_state()
    elif cmd == 'gen':
        # Generate all valid moves
        moves = generate_moves(game.board, game.rack, game.turn, game.chars)
        if moves:
            print()
            for idx, (coord, move_str, num_tiles) in enumerate(moves, 1):
                # Calculate leave (tiles remaining)
                leave = calculate_leave(game.rack, move_str)
                # Format: idx: coord move_str leave (keep commas in move string)
                print(f"{idx:3}: {coord:<4} {move_str:<15} {leave}")
        else:
            print("No valid moves found")
    else:
        print(f"Unknown command: {cmd}")
    
    return True


def main():
    """Main CLI loop"""
    game = AMathGame()
    
    print("a-math game CLI")
    print("Commands: new, commit <coord> <tiles>, n, p, turn <n>, s, reset, get <coord>, rack <tiles>|--random, gen")
    print("Type 'quit' or 'exit' to exit\n")
    
    while True:
        try:
            command = input("> ").strip()
            if not process_command(game, command):
                break
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()

