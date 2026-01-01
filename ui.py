"""UI and display functions for the game board and information."""

from tiles import get_tile_display


def get_board_char(i: int, j: int) -> str:
    """Get the character to display at board position (i, j) when empty"""
    # Return a dot for all empty squares
    return "."


def display_board(chars: dict, board: list):
    """Display the game board"""
    # Header - use 3-char spacing for multi-character tiles
    header = "   " + " ".join([chr(ord('A') + i).center(3) for i in range(15)])
    print(header)
    print("   " + "-" * (3 * 15 + 14))  # 3 chars per cell + spaces between
    
    # Board rows
    for i in range(15):
        row_num = str(i + 1).rjust(2)
        row_display = []
        for j in range(15):
            tile = board[i][j]
            if tile == ' ':
                # Show centered dot for empty spaces
                row_display.append("·".center(3))
            else:
                # Show tile key directly (e.g., "12", "×/÷", "+/-")
                if tile in chars:
                    # Display the actual tile key, not the UI
                    display_key = tile
                    # Handle blank tile specially
                    if tile == '?':
                        display_key = '?'
                    row_display.append(display_key.center(3))
                else:
                    row_display.append(tile.center(3))
        
        print(f"{row_num}|" + " ".join(row_display) + " |")
    
    print("   " + "-" * (3 * 15 + 14))


def display_info(chars: dict, bag: list, rack: list, turn: int):
    """Display game information"""
    bag_count = len(bag)
    unseen_total = bag_count  # Simplified for now
    
    print(f"Bag + unseen: ({unseen_total})")
    
    # Show bag contents (all tiles, formatted)
    bag_display = []
    for tile in bag:
        display = get_tile_display(chars, tile)
        bag_display.append(display)
    
    # Format into lines (similar to example)
    line = ""
    for tile_display in bag_display:
        if len(line) + len(tile_display) + 1 > 60:
            print(f"   {line}")
            line = tile_display
        else:
            if line:
                line += " " + tile_display
            else:
                line = tile_display
    if line:
        print(f"   {line}")
    
    # Show rack (8 tiles) - show just the keys for readability
    rack_display = " ".join([tile for tile in rack[:8]])
    print(f"\n   Rack ({len(rack)}): {rack_display}")
    
    # Show turn
    player = "me" if turn % 2 == 0 else "others"
    print(f"\n   Turn {turn}: ({player})")


def show_state(chars: dict, board: list, bag: list, rack: list, turn: int):
    """Show current game state"""
    display_board(chars, board)
    display_info(chars, bag, rack, turn)

