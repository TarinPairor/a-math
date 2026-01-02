"""
Algorithm to generate valid line vectors through existing tiles on the board.

A valid vector represents a line (horizontal or vertical) where new plays can be made
to extend existing equations. Vectors are filtered to avoid:
- 2-tile overlaps (would create invalid 2-tile equations)
- Vectors completely inside other vectors
- Overhanging vectors (disconnected from existing tiles)
"""

from typing import List, Tuple, Set
from collections import namedtuple

# Vector representation: (start_row, start_col, end_row, end_col, is_horizontal)
Vector = namedtuple('Vector', ['start_row', 'start_col', 'end_row', 'end_col', 'is_horizontal'])


def get_existing_tiles(board: List[List[str]]) -> Set[Tuple[int, int]]:
    """
    Get all positions on the board that contain tiles (non-empty).
    
    Args:
        board: 15x15 board where ' ' represents empty space
        
    Returns:
        Set of (row, col) tuples for all non-empty positions
    """
    tiles = set()
    for row in range(15):
        for col in range(15):
            if board[row][col] != ' ':
                tiles.add((row, col))
    return tiles


def find_existing_play_vectors(tiles: Set[Tuple[int, int]]) -> List[Vector]:
    """
    Find vectors representing existing plays (contiguous horizontal/vertical sequences).
    
    Args:
        tiles: Set of (row, col) positions with tiles
        
    Returns:
        List of Vector objects representing existing plays
    """
    vectors = []
    processed = set()
    
    # Find horizontal plays (contiguous tiles in same row)
    for row in range(15):
        for col in range(15):
            if (row, col) in tiles and (row, col) not in processed:
                # Find contiguous horizontal tiles
                end_col = col
                while end_col + 1 < 15 and (row, end_col + 1) in tiles:
                    end_col += 1
                
                # Mark all tiles in this play as processed
                for c in range(col, end_col + 1):
                    processed.add((row, c))
                
                # Only create vector if at least 2 tiles (a play, not just a single tile)
                if end_col > col:
                    vectors.append(Vector(row, col, row, end_col, True))
    
    # Find vertical plays (contiguous tiles in same column)
    for col in range(15):
        for row in range(15):
            if (row, col) in tiles and (row, col) not in processed:
                # Find contiguous vertical tiles
                end_row = row
                while end_row + 1 < 15 and (end_row + 1, col) in tiles:
                    end_row += 1
                
                # Mark all tiles in this play as processed
                for r in range(row, end_row + 1):
                    processed.add((r, col))
                
                # Only create vector if at least 2 tiles
                if end_row > row:
                    vectors.append(Vector(row, col, end_row, col, False))
    
    return vectors


def generate_extension_vectors(tiles: Set[Tuple[int, int]]) -> List[Vector]:
    """
    Generate all potential extension vectors (full rows/columns through existing tiles).
    
    Args:
        tiles: Set of (row, col) positions with tiles
        
    Returns:
        List of Vector objects representing potential extension lines
    """
    vectors = []
    
    # Group tiles by row and column
    rows_with_tiles = {}
    cols_with_tiles = {}
    
    for row, col in tiles:
        if row not in rows_with_tiles:
            rows_with_tiles[row] = []
        rows_with_tiles[row].append(col)
        
        if col not in cols_with_tiles:
            cols_with_tiles[col] = []
        cols_with_tiles[col].append(row)
    
    # Create horizontal vectors (entire rows with tiles)
    for row in rows_with_tiles:
        # Extend to full row (0 to 14)
        vectors.append(Vector(row, 0, row, 14, True))
    
    # Create vertical vectors (entire columns with tiles)
    for col in cols_with_tiles:
        # Extend to full column (0 to 14)
        vectors.append(Vector(0, col, 14, col, False))
    
    return vectors


def is_vector_inside(inner: Vector, outer: Vector) -> bool:
    """
    Check if inner vector is completely inside outer vector.
    
    Args:
        inner: Vector to check if inside
        outer: Vector to check if contains inner
        
    Returns:
        True if inner is completely contained within outer
    """
    if inner.is_horizontal != outer.is_horizontal:
        return False
    
    if inner.is_horizontal:
        # Both horizontal: check if same row and cols are inside
        return (inner.start_row == outer.start_row and
                outer.start_col <= inner.start_col and
                inner.end_col <= outer.end_col)
    else:
        # Both vertical: check if same col and rows are inside
        return (inner.start_col == outer.start_col and
                outer.start_row <= inner.start_row and
                inner.end_row <= outer.end_row)


def would_create_two_tile_overlap(vector: Vector, existing_vectors: List[Vector]) -> bool:
    """
    Check if a vector would create a 2-tile overlap with existing plays.
    A 2-tile overlap creates an invalid 2-tile equation.
    
    Args:
        vector: Vector to check
        existing_vectors: List of existing play vectors
        
    Returns:
        True if vector would create a 2-tile overlap
    """
    for existing_vec in existing_vectors:
        if vector.is_horizontal == existing_vec.is_horizontal:
            continue  # Parallel vectors don't create overlaps
        
        # Find intersection points
        intersections = []
        
        if vector.is_horizontal:
            # Vector is horizontal, existing is vertical
            for col in range(vector.start_col, vector.end_col + 1):
                if (existing_vec.start_col == col and
                    existing_vec.start_row <= vector.start_row <= existing_vec.end_row):
                    intersections.append((vector.start_row, col))
        else:
            # Vector is vertical, existing is horizontal
            for row in range(vector.start_row, vector.end_row + 1):
                if (existing_vec.start_row == row and
                    existing_vec.start_col <= vector.start_col <= existing_vec.end_col):
                    intersections.append((row, vector.start_col))
        
        # If exactly 2 adjacent intersection points, it's a 2-tile overlap
        if len(intersections) == 2:
            r1, c1 = intersections[0]
            r2, c2 = intersections[1]
            # Check if they're adjacent (horizontally or vertically)
            if abs(r1 - r2) + abs(c1 - c2) == 1:
                return True
    
    return False


def remove_overhanging_vectors(vectors: List[Vector], tiles: Set[Tuple[int, int]]) -> List[Vector]:
    """
    Remove vectors that don't contain any existing tiles (overhanging/disconnected).
    
    Args:
        vectors: List of vectors to filter
        tiles: Set of existing tile positions
        
    Returns:
        Filtered list of vectors that contain at least one existing tile
    """
    valid_vectors = []
    
    for vector in vectors:
        contains_tile = False
        
        if vector.is_horizontal:
            for col in range(vector.start_col, vector.end_col + 1):
                if (vector.start_row, col) in tiles:
                    contains_tile = True
                    break
        else:
            for row in range(vector.start_row, vector.end_row + 1):
                if (row, vector.start_col) in tiles:
                    contains_tile = True
                    break
        
        if contains_tile:
            valid_vectors.append(vector)
    
    return valid_vectors


def generate_valid_vectors(board: List[List[str]]) -> List[Vector]:
    """
    Main algorithm: Generate all valid line vectors through existing tiles.
    
    This algorithm:
    1. Finds all existing tiles on the board
    2. Identifies existing play vectors (contiguous sequences)
    3. Generates extension vectors (full rows/columns through tiles)
    4. Filters out invalid vectors (inside others, 2-tile overlaps, overhanging)
    
    Args:
        board: 15x15 board where ' ' represents empty space
        
    Returns:
        List of valid Vector objects representing playable lines
    """
    # Step 1: Get all existing tiles
    tiles = get_existing_tiles(board)
    
    if not tiles:
        return []  # No tiles on board, no valid vectors
    
    # Step 2: Find existing play vectors (for overlap checking)
    existing_play_vectors = find_existing_play_vectors(tiles)
    
    # Step 3: Generate all potential extension vectors
    extension_vectors = generate_extension_vectors(tiles)
    
    # Step 4: Filter out vectors that are inside other vectors
    valid_vectors = []
    for vec in extension_vectors:
        is_inside = False
        for other_vec in extension_vectors:
            if vec != other_vec and is_vector_inside(vec, other_vec):
                is_inside = True
                break
        if not is_inside:
            valid_vectors.append(vec)
    
    # Step 5: Filter out vectors that would create 2-tile overlaps
    valid_vectors = [vec for vec in valid_vectors 
                    if not would_create_two_tile_overlap(vec, existing_play_vectors)]
    
    # Step 6: Remove overhanging vectors (must contain at least one existing tile)
    valid_vectors = remove_overhanging_vectors(valid_vectors, tiles)
    
    return valid_vectors


def format_vector(vector: Vector) -> str:
    """
    Format a vector as a human-readable string.
    
    Args:
        vector: Vector to format
        
    Returns:
        String representation (e.g., "H8-H14" for vertical, "8C-8O" for horizontal)
    """
    start_letter = chr(ord('A') + vector.start_col)
    end_letter = chr(ord('A') + vector.end_col)
    start_num = vector.start_row + 1
    end_num = vector.end_row + 1
    
    if vector.is_horizontal:
        return f"{start_num}{start_letter}-{end_num}{end_letter}"
    else:
        return f"{start_letter}{start_num}-{end_letter}{end_num}"


# Example usage and testing
if __name__ == "__main__":
    # Example: Empty board
    empty_board = [[' ' for _ in range(15)] for _ in range(15)]
    vectors = generate_valid_vectors(empty_board)
    print(f"Empty board: {len(vectors)} valid vectors")
    
    # Example: Board with a horizontal play at row 8, columns C-H
    test_board = [[' ' for _ in range(15)] for _ in range(15)]
    # Mark tiles from 8C to 8H (row 7, cols 2-7)
    for col in range(2, 8):
        test_board[7][col] = 'X'  # Placeholder tile
    
    
    vectors = generate_valid_vectors(test_board)
    print(f"\nBoard with play at 8C-8H: {len(vectors)} valid vectors")
    for vec in vectors:
        print(f"  {format_vector(vec)}")

