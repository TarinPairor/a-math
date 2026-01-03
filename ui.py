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
                # Handle blank tiles: stored as "?value" format
                if tile.startswith('?'):
                    # Blank tile - show the value it represents with a visual marker
                    # Use combining low line (U+0332) to underline without taking space
                    blank_value = tile[1:]  # Get value after "?"
                    # Center the base value first (this gives us the correct spacing)
                    centered_base = blank_value.center(3)
                    # Now add combining underline only to non-space characters
                    # This preserves the centering while adding the visual marker
                    marked_value = ''.join(
                        char + '\u0332' if char != ' ' else ' '
                        for char in centered_base
                    )
                    row_display.append(marked_value)
                elif ':' in tile and tile.split(':', 1)[0] in ['×/÷', '+/-']:
                    # Locked compound tile - show the compound symbol (before :)
                    compound_symbol = tile.split(':', 1)[0]
                    row_display.append(compound_symbol.center(3))
                elif tile in chars:
                    # Display the actual tile key, not the UI
                    display_key = tile
                    row_display.append(display_key.center(3))
                else:
                    row_display.append(tile.center(3))
        
        print(f"{row_num}|" + " ".join(row_display) + " |")
    
    print("   " + "-" * (3 * 15 + 14))


def display_info(chars: dict, bag: list, rack: list, turn: int, bag_unseen_count: int = None, scores: list = None, player_names: list = None):
    """
    Display game information.
    
    Args:
        chars: Character definitions
        bag: Current bag (physical tiles remaining)
        rack: Current player's rack
        turn: Current turn number
        bag_unseen_count: Optional pre-calculated bag+unseen count
        scores: List of scores [player0_score, player1_score]
        player_names: List of player names [player0_name, player1_name]
    """
    # Display player scores (before bag+unseen)
    if scores is not None and player_names is not None:
        # Format: player_name score (right-aligned, similar to example)
        # Example: "euclid          57"
        #          "pythagoras      48"
        # We'll use a fixed width format to align scores
        max_name_len = max(len(name) for name in player_names) if player_names else 10
        for i, (name, score) in enumerate(zip(player_names, scores)):
            # Format: name (left-aligned) + spacing + score (right-aligned)
            # Use enough spacing to align scores nicely
            name_display = name.ljust(max_name_len + 2)
            score_display = str(score).rjust(4)
            print(f"{name_display} {score_display}")
    
    # Calculate bag+unseen if not provided
    if bag_unseen_count is None:
        total_tiles = sum(char_data['count'] for char_data in chars.values())
        # Count tiles on board (we need to get this from the game, but for now use bag count)
        # Actually, we'll calculate it: total - bag - rack
        bag_unseen_count = total_tiles - len(bag) - len(rack)
    
    print(f"Bag + unseen: ({bag_unseen_count})")
    
    # Show bag contents (all tiles, formatted and sorted)
    # Sort by tile key for consistent display
    sorted_bag = sorted(bag, key=lambda t: (chars.get(t, {}).get('index', 999), t))
    bag_display = []
    for tile in sorted_bag:
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


def show_state(chars: dict, board: list, bag: list, rack: list, turn: int, bag_unseen_count: int = None, scores: list = None, player_names: list = None):
    """Show current game state"""
    display_board(chars, board)
    display_info(chars, bag, rack, turn, bag_unseen_count, scores, player_names)

