"""
Simple board visualizer for A-Math.
Click to cycle through: empty -> N -> O -> - -> empty
"""

import tkinter as tk
from typing import Tuple, Optional

N = 15
CELL_SIZE = 30
GRID_PADDING = 50


class BoardVisualizer:
    def __init__(self, root):
        self.root = root
        self.root.title("A-Math Board Visualizer")
        
        # Board state: ' ' for empty, 'N', 'O', '-' for other states
        self.board = [[' ' for _ in range(N)] for _ in range(N)]
        
        # Highlighting state for "= gen" feature
        self.show_equals_candidates = False
        self.equals_candidates = set()  # Set of (row, col) tuples
        
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
        self.canvas.bind("<Button-1>", self.on_click)
        
        # Control buttons
        control_frame = tk.Frame(root)
        control_frame.pack(pady=5)
        
        tk.Button(control_frame, text="Reset", command=self.reset).pack(side=tk.LEFT, padx=5)
        tk.Button(control_frame, text="= gen", command=self.toggle_equals_gen).pack(side=tk.LEFT, padx=5)
        
        # Draw initial grid
        self.redraw()
    
    def coord_to_pixel(self, row: int, col: int) -> Tuple[int, int]:
        """Convert grid coordinates to pixel coordinates"""
        x = GRID_PADDING + col * CELL_SIZE
        y = GRID_PADDING + row * CELL_SIZE
        return x, y
    
    def pixel_to_coord(self, x: int, y: int) -> Optional[Tuple[int, int]]:
        """Convert pixel coordinates to grid coordinates"""
        col = (x - GRID_PADDING) // CELL_SIZE
        row = (y - GRID_PADDING) // CELL_SIZE
        
        if 0 <= row < N and 0 <= col < N:
            return row, col
        return None
    
    def is_occupied(self, row: int, col: int) -> bool:
        """Check if a cell is occupied (non-empty)"""
        if 0 <= row < N and 0 <= col < N:
            return self.board[row][col] != ' '
        return False
    
    def count_contiguous_in_direction(self, row: int, col: int, drow: int, dcol: int) -> int:
        """Count contiguous occupied cells in a given direction from an empty cell"""
        count = 0
        check_row, check_col = row + drow, col + dcol
        
        while 0 <= check_row < N and 0 <= check_col < N:
            if self.is_occupied(check_row, check_col):
                count += 1
                check_row += drow
                check_col += dcol
            else:
                break
        
        return count
    
    def is_adjacent_to_occupied(self, row: int, col: int) -> bool:
        """Check if an empty cell is adjacent (non-diagonal) to any occupied cell"""
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]  # up, down, left, right
        for drow, dcol in directions:
            adj_row, adj_col = row + drow, col + dcol
            if self.is_occupied(adj_row, adj_col):
                return True
        return False
    
    def get_equals_candidates(self) -> set:
        """
        Find candidate squares for placing '=' sign based on rules:
        1. Only empty boxes
        2. From non-empty squares, highlight contiguous sequences of 6 empty squares in all directions
        3. Remove squares adjacent to 'O's
        4. Remove squares below and to the right of '-'
        """
        candidates = set()
        
        # Rule 2: From each non-empty square, highlight 6 blocks in all 4 directions
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]  # up, down, left, right
        
        for row in range(N):
            for col in range(N):
                if self.is_occupied(row, col):
                    # Mark 6 squares in each direction
                    for drow, dcol in directions:
                        mark_row, mark_col = row + drow, col + dcol
                        for _ in range(6):
                            if 0 <= mark_row < N and 0 <= mark_col < N:
                                if self.board[mark_row][mark_col] == ' ':  # Rule 1: only empty
                                    candidates.add((mark_row, mark_col))
                                mark_row += drow
                                mark_col += dcol
        
        # Rule 3: Remove squares adjacent to 'O's
        candidates_filtered = set()
        for row, col in candidates:
            is_adjacent_to_O = False
            for drow, dcol in directions:
                adj_row, adj_col = row + drow, col + dcol
                if 0 <= adj_row < N and 0 <= adj_col < N:
                    if self.board[adj_row][adj_col] == 'O':
                        is_adjacent_to_O = True
                        break
            if not is_adjacent_to_O:
                candidates_filtered.add((row, col))
        
        candidates = candidates_filtered
        
        # Rule 4: Remove squares that are one space below a '-' OR one space to the right of '-'
        candidates_filtered = set()
        for row, col in candidates:
            should_remove = False
            # Check if this square is one space below a '-' (same column, row = '-' row + 1)
            if row > 0 and self.board[row - 1][col] == '-':
                should_remove = True
            # Check if this square is one space to the right of a '-' (same row, col = '-' col + 1)
            if not should_remove and col > 0 and self.board[row][col - 1] == '-':
                should_remove = True
            
            if not should_remove:
                candidates_filtered.add((row, col))
        
        return candidates_filtered
    
    def toggle_equals_gen(self):
        """Toggle the '= gen' highlighting mode"""
        self.show_equals_candidates = not self.show_equals_candidates
        if self.show_equals_candidates:
            self.equals_candidates = self.get_equals_candidates()
        else:
            self.equals_candidates = set()
        self.redraw()
    
    def redraw(self):
        """Redraw the entire grid"""
        self.canvas.delete("all")
        
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
                cell_value = self.board[row][col]
                
                # Determine fill color
                fill_color = 'white'
                if cell_value == ' ' and self.is_adjacent_to_occupied(row, col):
                    fill_color = 'light blue'
                
                # Draw cell rectangle
                self.canvas.create_rectangle(
                    x, y,
                    x + CELL_SIZE, y + CELL_SIZE,
                    fill=fill_color,
                    outline='black',
                    width=1
                )
                
                # Draw green overlay for "= gen" candidates (low opacity simulation with light green)
                if self.show_equals_candidates and (row, col) in self.equals_candidates:
                    self.canvas.create_rectangle(
                        x, y,
                        x + CELL_SIZE, y + CELL_SIZE,
                        fill='#CCFFCC',  # Light green to simulate low opacity
                        outline='',
                        stipple='gray50'  # Dither pattern for semi-transparency effect
                    )
                
                # Draw content based on board state
                if cell_value in ('N', 'O', '-'):
                    self.canvas.create_text(
                        x + CELL_SIZE // 2,
                        y + CELL_SIZE // 2,
                        text=cell_value,
                        font=('Arial', 16, 'bold'),
                        fill='black'
                    )
                elif cell_value == ' ' and self.is_adjacent_to_occupied(row, col):
                    # Show directional counts for adjacent empty squares
                    count_above = self.count_contiguous_in_direction(row, col, -1, 0)  # up
                    count_below = self.count_contiguous_in_direction(row, col, 1, 0)   # down
                    count_left = self.count_contiguous_in_direction(row, col, 0, -1)   # left
                    count_right = self.count_contiguous_in_direction(row, col, 0, 1)   # right
                    
                    # Draw counts on four sides
                    font_size = 8
                    offset = 2
                    
                    # Top (above)
                    if count_above > 0:
                        self.canvas.create_text(
                            x + CELL_SIZE // 2,
                            y + offset,
                            text=str(count_above),
                            font=('Arial', font_size),
                            fill='black',
                            anchor='n'
                        )
                    
                    # Bottom (below)
                    if count_below > 0:
                        self.canvas.create_text(
                            x + CELL_SIZE // 2,
                            y + CELL_SIZE - offset,
                            text=str(count_below),
                            font=('Arial', font_size),
                            fill='black',
                            anchor='s'
                        )
                    
                    # Left
                    if count_left > 0:
                        self.canvas.create_text(
                            x + offset,
                            y + CELL_SIZE // 2,
                            text=str(count_left),
                            font=('Arial', font_size),
                            fill='black',
                            anchor='w'
                        )
                    
                    # Right
                    if count_right > 0:
                        self.canvas.create_text(
                            x + CELL_SIZE - offset,
                            y + CELL_SIZE // 2,
                            text=str(count_right),
                            font=('Arial', font_size),
                            fill='black',
                            anchor='e'
                        )
    
    def on_click(self, event):
        """Handle click to cycle through states: empty -> N -> O -> - -> empty"""
        coord = self.pixel_to_coord(event.x, event.y)
        if coord is None:
            return
        
        row, col = coord
        
        # Cycle through states: empty -> N -> O -> - -> empty
        current = self.board[row][col]
        if current == ' ':
            self.board[row][col] = 'N'
        elif current == 'N':
            self.board[row][col] = 'O'
        elif current == 'O':
            self.board[row][col] = '-'
        else:  # current == '-'
            self.board[row][col] = ' '
        
        # Redraw
        if self.show_equals_candidates:
            self.equals_candidates = self.get_equals_candidates()
        self.redraw()
    
    def reset(self):
        """Reset the board"""
        self.board = [[' ' for _ in range(N)] for _ in range(N)]
        self.show_equals_candidates = False
        self.equals_candidates = set()
        self.redraw()


def main():
    root = tk.Tk()
    app = BoardVisualizer(root)
    root.mainloop()


if __name__ == "__main__":
    main()

