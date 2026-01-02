"""
Tkinter UI for visualizing valid play vectors using vector_generator.py
Shows marked tiles, valid cells (green), invalid cells (red), and arrows through valid vectors.
"""

import tkinter as tk
from typing import List, Tuple, Set
from vector_generator import generate_valid_vectors, Vector, get_existing_tiles

N = 15
CELL_SIZE = 30
GRID_PADDING = 50

# Center square is at (7, 7) - row 8, column H
CENTER_SQUARE = (7, 7)


class VectorVisualizer:
    def __init__(self, root):
        self.root = root
        self.root.title("A-Math Vector Visualizer")
        
        # Board state: ' ' for empty, any other char for marked tile
        self.board = [[' ' for _ in range(N)] for _ in range(N)]
        
        # UI constants
        canvas_width = GRID_PADDING * 2 + CELL_SIZE * N
        canvas_height = GRID_PADDING * 2 + CELL_SIZE * N
        
        self.canvas = tk.Canvas(
            root,
            width=canvas_width,
            height=canvas_height,
            bg='white'
        )
        self.canvas.pack(padx=10, pady=10)
        
        # Bind click event
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        
        # Control buttons
        control_frame = tk.Frame(root)
        control_frame.pack(pady=5)
        
        tk.Button(control_frame, text="Clear All", command=self.clear_all).pack(side=tk.LEFT, padx=5)
        tk.Button(control_frame, text="Reset", command=self.reset).pack(side=tk.LEFT, padx=5)
        
        # Status label
        self.status_label = tk.Label(
            root,
            text="Click tiles to mark them. Green = valid, Red = invalid, Blue = adjacent to marked, Arrows show valid vectors",
            font=('Arial', 10)
        )
        self.status_label.pack(pady=5)
        
        # Draw initial grid
        self.redraw()
    
    def coord_to_pixel(self, row: int, col: int) -> Tuple[int, int]:
        """Convert grid coordinates to pixel coordinates"""
        x = GRID_PADDING + col * CELL_SIZE
        y = GRID_PADDING + row * CELL_SIZE
        return x, y
    
    def pixel_to_coord(self, x: int, y: int) -> Tuple[int, int] | None:
        """Convert pixel coordinates to grid coordinates"""
        col = (x - GRID_PADDING) // CELL_SIZE
        row = (y - GRID_PADDING) // CELL_SIZE
        
        if 0 <= row < N and 0 <= col < N:
            return row, col
        return None
    
    def count_adjacent_marked(self, row: int, col: int) -> Tuple[int, int]:
        """
        Count how many marked cells are horizontally and vertically adjacent to a cell.
        Returns (horizontal_count, vertical_count)
        """
        h_count = 0  # Horizontal adjacent (left and right)
        v_count = 0  # Vertical adjacent (up and down)
        
        # Check left and right (horizontal)
        if col > 0 and self.board[row][col - 1] != ' ':
            h_count += 1
        if col < N - 1 and self.board[row][col + 1] != ' ':
            h_count += 1
        
        # Check up and down (vertical)
        if row > 0 and self.board[row - 1][col] != ' ':
            v_count += 1
        if row < N - 1 and self.board[row + 1][col] != ' ':
            v_count += 1
        
        return h_count, v_count
    
    def is_invalid_adjacent_for_vector(self, h_count: int, v_count: int, is_horizontal: bool) -> bool:
        """
        Check if an adjacent cell count makes it invalid for a vector.
        For horizontal vectors: invalid if (0/1), (1/1), or (2/1)
        For vertical vectors: invalid if (1/0), (1/1), or (1/2)
        """
        if is_horizontal:
            # Horizontal vector: invalid if (0/1), (1/1), or (2/1)
            return (h_count, v_count) in [(0, 1), (1, 1), (2, 1)]
        else:
            # Vertical vector: invalid if (1/0), (1/1), or (1/2)
            return (h_count, v_count) in [(1, 0), (1, 1), (1, 2)]
    
    def filter_vectors_by_adjacent(self, vectors: List[Vector], adjacent_counts: List[List[Tuple[int, int] | None]]) -> List[Vector]:
        """
        Filter vectors by removing parts that contain invalid adjacent cells.
        Splits vectors into sub-vectors that exclude invalid adjacent cells.
        
        For horizontal vectors: invalid adjacent cells have (0/1), (1/1), or (2/1)
        For vertical vectors: invalid adjacent cells have (1/0), (1/1), or (1/2)
        """
        filtered_vectors = []
        
        for vector in vectors:
            if vector.is_horizontal:
                # Horizontal vector: check each column along the row
                row = vector.start_row
                valid_segments = []
                segment_start = None
                
                for col in range(vector.start_col, vector.end_col + 1):
                    # Check if this cell has an invalid adjacent count
                    count = adjacent_counts[row][col]
                    is_invalid = False
                    
                    if count is not None:
                        h_count, v_count = count
                        is_invalid = self.is_invalid_adjacent_for_vector(h_count, v_count, True)
                    
                    if not is_invalid:
                        # This cell is valid, continue or start a segment
                        if segment_start is None:
                            segment_start = col
                    else:
                        # This cell is invalid, end current segment if exists
                        if segment_start is not None:
                            segment_end = col - 1
                            if segment_end > segment_start:  # At least 2 cells
                                valid_segments.append((segment_start, segment_end))
                            segment_start = None
                
                # Handle segment that extends to the end
                if segment_start is not None:
                    segment_end = vector.end_col
                    if segment_end > segment_start:  # At least 2 cells
                        valid_segments.append((segment_start, segment_end))
                
                # Create sub-vectors for each valid segment
                for start_col, end_col in valid_segments:
                    if end_col > start_col:  # At least 2 cells (end_col - start_col >= 1)
                        filtered_vectors.append(Vector(row, start_col, row, end_col, True))
            
            else:
                # Vertical vector: check each row along the column
                col = vector.start_col
                valid_segments = []
                segment_start = None
                
                for row in range(vector.start_row, vector.end_row + 1):
                    # Check if this cell has an invalid adjacent count
                    count = adjacent_counts[row][col]
                    is_invalid = False
                    
                    if count is not None:
                        h_count, v_count = count
                        is_invalid = self.is_invalid_adjacent_for_vector(h_count, v_count, False)
                    
                    if not is_invalid:
                        # This cell is valid, continue or start a segment
                        if segment_start is None:
                            segment_start = row
                    else:
                        # This cell is invalid, end current segment if exists
                        if segment_start is not None:
                            segment_end = row - 1
                            if segment_end > segment_start:  # At least 2 cells
                                valid_segments.append((segment_start, segment_end))
                            segment_start = None
                
                # Handle segment that extends to the end
                if segment_start is not None:
                    segment_end = vector.end_row
                    if segment_end > segment_start:  # At least 2 cells
                        valid_segments.append((segment_start, segment_end))
                
                # Create sub-vectors for each valid segment
                for start_row, end_row in valid_segments:
                    if end_row > start_row:  # At least 2 cells (end_row - start_row >= 1)
                        filtered_vectors.append(Vector(start_row, col, end_row, col, False))
        
        return filtered_vectors
    
    def filter_vectors_with_marked_tiles(self, vectors: List[Vector]) -> List[Vector]:
        """
        Remove all vectors that don't contain at least one marked tile (X).
        """
        filtered = []
        
        for vector in vectors:
            contains_marked = False
            
            if vector.is_horizontal:
                # Check if any cell in this horizontal vector is marked
                row = vector.start_row
                for col in range(vector.start_col, vector.end_col + 1):
                    if self.board[row][col] != ' ':
                        contains_marked = True
                        break
            else:
                # Check if any cell in this vertical vector is marked
                col = vector.start_col
                for row in range(vector.start_row, vector.end_row + 1):
                    if self.board[row][col] != ' ':
                        contains_marked = True
                        break
            
            if contains_marked:
                filtered.append(vector)
        
        return filtered
    
    def compute_cell_states(self, valid_vectors: List[Vector]) -> Tuple[List[List[str]], List[List[Tuple[int, int] | None]]]:
        """
        Compute cell states for all cells based on valid vectors.
        Returns:
            - states: 15x15 grid of states: 'marked', 'valid', 'adjacent_invalid', or 'invalid'
            - adjacent_counts: 15x15 grid of (h_count, v_count) tuples for adjacent cells, None otherwise
        """
        states = [['invalid' for _ in range(N)] for _ in range(N)]
        adjacent_counts = [[None for _ in range(N)] for _ in range(N)]
        
        # Mark all cells with tiles as 'marked'
        for row in range(N):
            for col in range(N):
                if self.board[row][col] != ' ':
                    states[row][col] = 'marked'
        
        # Mark cells adjacent to marked tiles as 'adjacent_invalid' (blue)
        # and count their adjacent marked cells
        for row in range(N):
            for col in range(N):
                if self.board[row][col] != ' ':  # This is a marked tile
                    # Check all 4 adjacent cells (up, down, left, right)
                    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        adj_row = row + dr
                        adj_col = col + dc
                        # Only mark if within bounds and not already marked
                        if (0 <= adj_row < N and 0 <= adj_col < N and 
                            states[adj_row][adj_col] != 'marked'):
                            states[adj_row][adj_col] = 'adjacent_invalid'
                            # Count adjacent marked cells for this adjacent cell
                            h_count, v_count = self.count_adjacent_marked(adj_row, adj_col)
                            adjacent_counts[adj_row][adj_col] = (h_count, v_count)
        
        # Mark cells on valid vectors as 'valid' (but not if already marked or adjacent_invalid)
        # This will be updated after filtering in redraw()
        for vector in valid_vectors:
            if vector.is_horizontal:
                row = vector.start_row
                for col in range(vector.start_col, vector.end_col + 1):
                    if states[row][col] not in ['marked', 'adjacent_invalid']:
                        states[row][col] = 'valid'
            else:
                col = vector.start_col
                for row in range(vector.start_row, vector.end_row + 1):
                    if states[row][col] not in ['marked', 'adjacent_invalid']:
                        states[row][col] = 'valid'
        
        return states, adjacent_counts
    
    def redraw(self):
        """Redraw the entire grid"""
        self.canvas.delete("all")
        
        # Get valid vectors once
        valid_vectors = generate_valid_vectors(self.board)
        
        # Compute all cell states and adjacent counts (using original vectors)
        cell_states, adjacent_counts = self.compute_cell_states(valid_vectors)
        
        # Filter vectors by removing parts with invalid adjacent cells
        filtered_vectors = self.filter_vectors_by_adjacent(valid_vectors, adjacent_counts)
        
        # Remove vectors that don't contain any marked tiles
        filtered_vectors = self.filter_vectors_with_marked_tiles(filtered_vectors)
        
        # Update cell states based on filtered vectors (re-mark valid cells)
        # First, reset valid cells that were marked by original vectors
        for row in range(N):
            for col in range(N):
                if cell_states[row][col] == 'valid':
                    cell_states[row][col] = 'invalid'
        
        # Mark cells on filtered valid vectors as 'valid' (but not if already marked or adjacent_invalid)
        for vector in filtered_vectors:
            if vector.is_horizontal:
                row = vector.start_row
                for col in range(vector.start_col, vector.end_col + 1):
                    if cell_states[row][col] not in ['marked', 'adjacent_invalid']:
                        cell_states[row][col] = 'valid'
            else:
                col = vector.start_col
                for row in range(vector.start_row, vector.end_row + 1):
                    if cell_states[row][col] not in ['marked', 'adjacent_invalid']:
                        cell_states[row][col] = 'valid'
        
        # Draw column labels (A-O)
        for col in range(N):
            letter = chr(ord('A') + col)
            x, y = self.coord_to_pixel(-1, col)
            self.canvas.create_text(
                x + CELL_SIZE // 2,
                y + CELL_SIZE // 2,
                text=letter,
                font=('Arial', 10, 'bold')
            )
        
        # Draw row labels (1-15)
        for row in range(N):
            number = str(row + 1)
            x, y = self.coord_to_pixel(row, -1)
            self.canvas.create_text(
                x + CELL_SIZE // 2,
                y + CELL_SIZE // 2,
                text=number,
                font=('Arial', 10, 'bold')
            )
        
        # Draw grid cells
        for row in range(N):
            for col in range(N):
                x, y = self.coord_to_pixel(row, col)
                
                # Get cell state
                state = cell_states[row][col]
                
                # Determine fill color
                if state == 'marked':
                    fill_color = 'lightgray'
                elif state == 'valid':
                    fill_color = 'lightgreen'
                elif state == 'adjacent_invalid':
                    fill_color = 'lightblue'  # Blue for adjacent to marked tiles
                else:  # invalid
                    fill_color = 'lightcoral'
                
                # Highlight center square
                if (row, col) == CENTER_SQUARE and state != 'marked':
                    if fill_color == 'lightcoral':
                        fill_color = '#FFB6C1'  # Light pink for invalid center
                    elif fill_color == 'lightgreen':
                        fill_color = '#90EE90'  # Slightly brighter green
                    elif fill_color == 'lightblue':
                        fill_color = '#87CEEB'  # Sky blue for adjacent center
                
                # Draw cell rectangle
                self.canvas.create_rectangle(
                    x, y,
                    x + CELL_SIZE, y + CELL_SIZE,
                    fill=fill_color,
                    outline='black',
                    width=1
                )
                
                # Draw marked tile indicator
                if state == 'marked':
                    self.canvas.create_text(
                        x + CELL_SIZE // 2,
                        y + CELL_SIZE // 2,
                        text='X',
                        font=('Arial', 16, 'bold'),
                        fill='black'
                    )
                
                # Draw adjacent count for lightblue cells
                if state == 'adjacent_invalid' and adjacent_counts[row][col] is not None:
                    h_count, v_count = adjacent_counts[row][col]
                    count_text = f"{h_count}/{v_count}"
                    self.canvas.create_text(
                        x + CELL_SIZE // 2,
                        y + CELL_SIZE // 2,
                        text=count_text,
                        font=('Arial', 9, 'bold'),
                        fill='darkblue'
                    )
        
        # Draw arrows for filtered valid vectors (through green cells)
        for vector in filtered_vectors:
            self.draw_vector_arrow(vector)
        
        # Update status
        marked_count = sum(1 for row in self.board for cell in row if cell != ' ')
        self.status_label.config(
            text=f"Marked: {marked_count} | Valid vectors: {len(filtered_vectors)} (filtered from {len(valid_vectors)}) | Click tiles to mark/unmark"
        )
    
    def draw_vector_arrow(self, vector: Vector):
        """Draw an arrow along a valid vector"""
        start_x, start_y = self.coord_to_pixel(vector.start_row, vector.start_col)
        end_x, end_y = self.coord_to_pixel(vector.end_row, vector.end_col)
        
        # Center the coordinates in the cells
        start_x += CELL_SIZE // 2
        start_y += CELL_SIZE // 2
        end_x += CELL_SIZE // 2
        end_y += CELL_SIZE // 2
        
        # Draw arrow
        if vector.is_horizontal:
            # Rightward arrow
            self.canvas.create_line(
                start_x, start_y,
                end_x, end_y,
                fill='green',
                width=3,
                arrow=tk.LAST,
                arrowshape=(8, 10, 3)
            )
        else:
            # Downward arrow
            self.canvas.create_line(
                start_x, start_y,
                end_x, end_y,
                fill='green',
                width=3,
                arrow=tk.LAST,
                arrowshape=(8, 10, 3)
            )
    
    def on_canvas_click(self, event):
        """Handle canvas click to mark/unmark tiles"""
        coord = self.pixel_to_coord(event.x, event.y)
        if coord is None:
            return
        
        row, col = coord
        
        # Toggle marked state
        if self.board[row][col] != ' ':
            self.board[row][col] = ' '
        else:
            self.board[row][col] = 'X'  # Mark with 'X' to indicate tile
        
        # Redraw
        self.redraw()
    
    def clear_all(self):
        """Clear all marked tiles"""
        self.board = [[' ' for _ in range(N)] for _ in range(N)]
        self.redraw()
    
    def reset(self):
        """Reset everything"""
        self.clear_all()


def main():
    root = tk.Tk()
    app = VectorVisualizer(root)
    root.mainloop()


if __name__ == "__main__":
    main()

