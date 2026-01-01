"""Command processing and CLI interface."""

from game import AMathGame
from ui import show_state
from tiles import get_tile_display, resolve_tile
from generator import generate_moves


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
        # game.show_state()
    elif cmd == 'commit':
        if len(parts) < 3:
            print("Usage: commit <coord> <tiles>")
            print("Example: commit 8G 1,+,12,+/-,3,=,.,.")
            return True
        coord = parts[1]
        # Join all parts after coord to handle comma-separated tiles
        tiles_str = ' '.join(parts[2:])
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
            print("Usage: rack <tiles>")
            print("Example: rack 0,1,2,3,4,5,6,7 or rack 0,+,*,/,=,?,21,22")
            print("(must provide exactly 8 tiles - can use indices or aliases)")
            return True
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
                # Format: idx, coordinate, move
                print(f"{idx:3}: {coord:<4} {move_str}")
        else:
            print("No valid moves found")
    else:
        print(f"Unknown command: {cmd}")
    
    return True


def main():
    """Main CLI loop"""
    game = AMathGame()
    
    print("a-math game CLI")
    print("Commands: new, commit <coord> <tiles>, n, p, turn <n>, s, reset, get <coord>, rack <tiles>, gen")
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

