"""
Simple board visualizer for A-Math.
Click to cycle through: empty -> X -> = -> empty
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
        
        # Board state: ' ' for empty, 'X' for marked, '=' for equals
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
        self.canvas.bind("<Button-1>", self.on_click)
        
        # Control buttons
        control_frame = tk.Frame(root)
        control_frame.pack(pady=5)
        
        tk.Button(control_frame, text="Reset", command=self.reset).pack(side=tk.LEFT, padx=5)
        
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
    
    def row_col_to_coord(self, row: int, col: int, horizontal: bool = True) -> str:
        """Convert row, col to coordinate string
        If horizontal: format as "8A" (number then letter)
        If vertical: format as "A8" (letter then number)
        """
        letter = chr(ord('A') + col)
        number = str(row + 1)
        if horizontal:
            return f"{number}{letter}"
        else:
            return f"{letter}{number}"
    
    def get_green_lines(self) -> list:
        """Return all green lines as coordinate strings
        Horizontal lines: format as "8A-8K" (number-char to number-char)
        Vertical lines: format as "A8-K8" (char-number to char-number)
        """
        green_cells = self.get_green_highlight_cells()
        if not green_cells:
            return []
        
        lines = []
        
        # Group green cells into horizontal and vertical lines
        # Horizontal lines: same row, contiguous columns
        processed = set()
        
        # Find horizontal lines
        for row in range(N):
            col = 0
            while col < N:
                if (row, col) in green_cells and (row, col) not in processed:
                    # Start of a horizontal line
                    start_col = col
                    # Find the end of the line
                    while col < N and (row, col) in green_cells:
                        processed.add((row, col))
                        col += 1
                    end_col = col - 1
                    
                    # Only add if line has at least 2 cells (or we want single cells too?)
                    if start_col <= end_col:
                        start_coord = self.row_col_to_coord(row, start_col, horizontal=True)
                        end_coord = self.row_col_to_coord(row, end_col, horizontal=True)
                        lines.append(f"{start_coord}-{end_coord}")
                else:
                    col += 1
        
        # Find vertical lines
        processed_vertical = set()
        for col in range(N):
            row = 0
            while row < N:
                if (row, col) in green_cells and (row, col) not in processed_vertical:
                    # Start of a vertical line
                    start_row = row
                    # Find the end of the line
                    while row < N and (row, col) in green_cells:
                        processed_vertical.add((row, col))
                        row += 1
                    end_row = row - 1
                    
                    # Only add if line has at least 2 cells (or we want single cells too?)
                    if start_row <= end_row:
                        start_coord = self.row_col_to_coord(start_row, col, horizontal=False)
                        end_coord = self.row_col_to_coord(end_row, col, horizontal=False)
                        lines.append(f"{start_coord}-{end_coord}")
                else:
                    row += 1
        
        return lines
    
    def get_green_highlight_cells(self) -> set:
        """Get cells that should be highlighted green from '=' signs"""
        green_cells = set()
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]  # up, down, left, right
        
        # Find all '=' signs
        for row in range(N):
            for col in range(N):
                if self.board[row][col] == '=':
                    # Extend line in all 4 directions
                    for drow, dcol in directions:
                        cells_counted = 0
                        check_row, check_col = row + drow, col + dcol
                        
                        # Continue until we've counted 7 cells or reached board boundary
                        while cells_counted < 7 and 0 <= check_row < N and 0 <= check_col < N:
                            if self.is_occupied(check_row, check_col):
                                # Skip occupied cell, continue to next
                                check_row += drow
                                check_col += dcol
                                continue
                            
                            # Check if this empty cell should stop the line
                            # For vertical lines (up/down), check perpendicular axis (left/right)
                            # For horizontal lines (left/right), check perpendicular axis (up/down)
                            # Stop only when EXACTLY 1 on one side (and 0 on other) OR exactly 1 on both sides
                            should_stop = False
                            if drow != 0:  # Vertical line (up or down)
                                # Check perpendicular axis: left and right
                                count_left = self.count_contiguous_in_direction(check_row, check_col, 0, -1)
                                count_right = self.count_contiguous_in_direction(check_row, check_col, 0, 1)
                                # Stop if: (1 on left AND 0 on right) OR (0 on left AND 1 on right) OR (1 on both)
                                if (count_left == 1 and count_right == 0) or (count_left == 0 and count_right == 1) or (count_left == 1 and count_right == 1):
                                    should_stop = True
                            else:  # Horizontal line (left or right)
                                # Check perpendicular axis: up and down
                                count_above = self.count_contiguous_in_direction(check_row, check_col, -1, 0)
                                count_below = self.count_contiguous_in_direction(check_row, check_col, 1, 0)
                                # Stop if: (1 above AND 0 below) OR (0 above AND 1 below) OR (1 on both)
                                if (count_above == 1 and count_below == 0) or (count_above == 0 and count_below == 1) or (count_above == 1 and count_below == 1):
                                    should_stop = True
                            
                            if should_stop:
                                # Stop before this cell
                                break
                            
                            # Mark this empty cell as green
                            green_cells.add((check_row, check_col))
                            cells_counted += 1
                            check_row += drow
                            check_col += dcol
        
        return green_cells
    
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
        
        # Get green highlight cells from '=' signs
        green_cells = self.get_green_highlight_cells()
        
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
                
                # Draw green overlay for cells in green highlight set
                if (row, col) in green_cells:
                    self.canvas.create_rectangle(
                        x, y,
                        x + CELL_SIZE, y + CELL_SIZE,
                        fill='light green',
                        outline='',
                        stipple='gray50'  # Dither pattern for semi-transparency effect
                    )
                
                # Draw content based on board state
                if cell_value == 'X':
                    self.canvas.create_text(
                        x + CELL_SIZE // 2,
                        y + CELL_SIZE // 2,
                        text='X',
                        font=('Arial', 16, 'bold'),
                        fill='black'
                    )
                elif cell_value == '=':
                    self.canvas.create_text(
                        x + CELL_SIZE // 2,
                        y + CELL_SIZE // 2,
                        text='=',
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
        """Handle click to cycle through states: empty -> X -> = -> empty"""
        coord = self.pixel_to_coord(event.x, event.y)
        if coord is None:
            return
        
        row, col = coord
        
        # Cycle through states: empty -> X -> = -> empty
        current = self.board[row][col]
        if current == ' ':
            self.board[row][col] = 'X'
        elif current == 'X':
            self.board[row][col] = '='
        else:  # current == '='
            self.board[row][col] = ' '
        
        # Redraw
        self.redraw()
    
    def reset(self):
        """Reset the board"""
        self.board = [[' ' for _ in range(N)] for _ in range(N)]
        self.redraw()


def main():
    root = tk.Tk()
    app = BoardVisualizer(root)
    root.mainloop()


if __name__ == "__main__":
    main()
