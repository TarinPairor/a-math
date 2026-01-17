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
        
        # State for showing arrows
        self.show_arrows = False
        self.show_long_arrows = False
        
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
        tk.Button(control_frame, text="Toggle Arrows", command=self.toggle_arrows).pack(side=tk.LEFT, padx=5)
        tk.Button(control_frame, text="Long Arrows", command=self.toggle_long_arrows).pack(side=tk.LEFT, padx=5)
        
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
    
    @staticmethod
    def _is_one_or_two(val: int) -> bool:
        """Helper function to check if value is 1 or 2"""
        return val == 1 or val == 2
    
    def is_dark_blue_cell(self, row: int, col: int) -> bool:
        """Check if a cell is a dark blue cell (adjacent to occupied AND has >2 contiguous blocks on any side)"""
        if self.board[row][col] != ' ' or not self.is_adjacent_to_occupied(row, col):
            return False
        
        # Check if any side has more than 2 contiguous adjacent blocks
        count_above = self.count_contiguous_in_direction(row, col, -1, 0)
        count_below = self.count_contiguous_in_direction(row, col, 1, 0)
        count_left = self.count_contiguous_in_direction(row, col, 0, -1)
        count_right = self.count_contiguous_in_direction(row, col, 0, 1)
        
        return count_above > 2 or count_below > 2 or count_left > 2 or count_right > 2
    
    def distance_to_nearest_occupied_or_dark_blue_x(self, row: int, col: int) -> int:
        """Calculate distance to nearest occupied cell or dark blue cell on x-axis (horizontal direction)"""
        min_dist = float('inf')
        # Check left
        for c in range(col - 1, -1, -1):
            if self.is_occupied(row, c) or self.is_dark_blue_cell(row, c):
                min_dist = min(min_dist, col - c)
                break
        # Check right
        for c in range(col + 1, N):
            if self.is_occupied(row, c) or self.is_dark_blue_cell(row, c):
                min_dist = min(min_dist, c - col)
                break
        return min_dist if min_dist != float('inf') else N  # Return N if not found
    
    def distance_to_nearest_occupied_or_dark_blue_y(self, row: int, col: int) -> int:
        """Calculate distance to nearest occupied cell or dark blue cell on y-axis (vertical direction)"""
        min_dist = float('inf')
        # Check above
        for r in range(row - 1, -1, -1):
            if self.is_occupied(r, col) or self.is_dark_blue_cell(r, col):
                min_dist = min(min_dist, row - r)
                break
        # Check below
        for r in range(row + 1, N):
            if self.is_occupied(r, col) or self.is_dark_blue_cell(r, col):
                min_dist = min(min_dist, r - row)
                break
        return min_dist if min_dist != float('inf') else N  # Return N if not found
    
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
    
    def toggle_arrows(self):
        """Toggle the display of arrows in each cell"""
        self.show_arrows = not self.show_arrows
        self.redraw()
    
    def toggle_long_arrows(self):
        """Toggle the display of long arrows (combining contiguous arrows)"""
        self.show_long_arrows = not self.show_long_arrows
        # Ensure arrows are enabled when long arrows is enabled
        if self.show_long_arrows:
            self.show_arrows = True
        self.redraw()
    
    def draw_arrow_down(self, x: int, y: int, size: int):
        """Draw a downward arrow in a cell (positioned in left half)"""
        # Position in left half of cell
        arrow_x = x + CELL_SIZE // 4
        arrow_y_start = y + CELL_SIZE // 4
        arrow_length = size * 0.8
        arrow_width = size * 0.25
        
        # Vertical line
        self.canvas.create_line(
            arrow_x, arrow_y_start,
            arrow_x, arrow_y_start + arrow_length,
            fill='black',
            width=1
        )
        
        # Arrow head (V shape pointing down)
        self.canvas.create_line(
            arrow_x, arrow_y_start + arrow_length,
            arrow_x - arrow_width // 2, arrow_y_start + arrow_length - arrow_width,
            fill='black',
            width=1
        )
        self.canvas.create_line(
            arrow_x, arrow_y_start + arrow_length,
            arrow_x + arrow_width // 2, arrow_y_start + arrow_length - arrow_width,
            fill='black',
            width=1
        )
    
    def draw_arrow_right(self, x: int, y: int, size: int):
        """Draw a rightward arrow in a cell (positioned in right half)"""
        # Position in right half of cell
        arrow_x_start = x + CELL_SIZE // 2
        arrow_y = y + 3 * CELL_SIZE // 4
        arrow_length = size * 0.8
        arrow_width = size * 0.25
        
        # Horizontal line
        self.canvas.create_line(
            arrow_x_start, arrow_y,
            arrow_x_start + arrow_length, arrow_y,
            fill='black',
            width=1
        )
        
        # Arrow head (> shape pointing right)
        self.canvas.create_line(
            arrow_x_start + arrow_length, arrow_y,
            arrow_x_start + arrow_length - arrow_width, arrow_y - arrow_width // 2,
            fill='black',
            width=1
        )
        self.canvas.create_line(
            arrow_x_start + arrow_length, arrow_y,
            arrow_x_start + arrow_length - arrow_width, arrow_y + arrow_width // 2,
            fill='black',
            width=1
        )
    
    def draw_long_arrow_down(self, start_row: int, end_row: int, col: int):
        """Draw a long downward arrow spanning multiple rows in a column"""
        start_x, start_y = self.coord_to_pixel(start_row, col)
        end_x, end_y = self.coord_to_pixel(end_row + 1, col)
        
        # Position in left half of column
        arrow_x = start_x + CELL_SIZE // 4
        arrow_y_start = start_y + CELL_SIZE // 4
        arrow_y_end = end_y - CELL_SIZE // 4
        arrow_width = CELL_SIZE * 0.125
        
        # Vertical line
        self.canvas.create_line(
            arrow_x, arrow_y_start,
            arrow_x, arrow_y_end,
            fill='black',
            width=2
        )
        
        # Arrow head (V shape pointing down) at bottom
        self.canvas.create_line(
            arrow_x, arrow_y_end,
            arrow_x - arrow_width, arrow_y_end - arrow_width * 2,
            fill='black',
            width=2
        )
        self.canvas.create_line(
            arrow_x, arrow_y_end,
            arrow_x + arrow_width, arrow_y_end - arrow_width * 2,
            fill='black',
            width=2
        )
    
    def draw_long_arrow_right(self, row: int, start_col: int, end_col: int):
        """Draw a long rightward arrow spanning multiple columns in a row"""
        start_x, start_y = self.coord_to_pixel(row, start_col)
        end_x, end_y = self.coord_to_pixel(row, end_col + 1)
        
        # Position in bottom half of row
        arrow_x_start = start_x + CELL_SIZE // 2
        arrow_x_end = end_x - CELL_SIZE // 2
        arrow_y = start_y + 3 * CELL_SIZE // 4
        arrow_width = CELL_SIZE * 0.125
        
        # Horizontal line
        self.canvas.create_line(
            arrow_x_start, arrow_y,
            arrow_x_end, arrow_y,
            fill='black',
            width=2
        )
        
        # Arrow head (> shape pointing right) at right end
        self.canvas.create_line(
            arrow_x_end, arrow_y,
            arrow_x_end - arrow_width * 2, arrow_y - arrow_width,
            fill='black',
            width=2
        )
        self.canvas.create_line(
            arrow_x_end, arrow_y,
            arrow_x_end - arrow_width * 2, arrow_y + arrow_width,
            fill='black',
            width=2
        )
    
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
        
        # Collect arrow information for all cells first
        down_arrows = [[False for _ in range(N)] for _ in range(N)]
        right_arrows = [[False for _ in range(N)] for _ in range(N)]
        
        if self.show_arrows:
            for row in range(N):
                for col in range(N):
                    cell_value = self.board[row][col]
                    if cell_value == ' ':
                        # Calculate directional counts for this cell
                        count_above = self.count_contiguous_in_direction(row, col, -1, 0)  # up
                        count_below = self.count_contiguous_in_direction(row, col, 1, 0)   # down
                        count_left = self.count_contiguous_in_direction(row, col, 0, -1)   # left
                        count_right = self.count_contiguous_in_direction(row, col, 0, 1)   # right
                        
                        # Default: show both arrows
                        show_down_arrow = True
                        show_right_arrow = True
                        
                        # Apply all arrow rules (same as before)
                        if ((self._is_one_or_two(count_above) and self._is_one_or_two(count_left) and count_below == 0 and count_right == 0) or \
                            (self._is_one_or_two(count_above) and self._is_one_or_two(count_right) and count_below == 0 and count_left == 0) or \
                            (self._is_one_or_two(count_below) and self._is_one_or_two(count_left) and count_above == 0 and count_right == 0) or \
                            (self._is_one_or_two(count_below) and self._is_one_or_two(count_right) and count_above == 0 and count_left == 0)):
                            show_down_arrow = False
                            show_right_arrow = False
                        elif ((self._is_one_or_two(count_above)) + (self._is_one_or_two(count_below)) + (self._is_one_or_two(count_left)) + (self._is_one_or_two(count_right))) == 3:
                            if count_left == 0:
                                show_right_arrow = True
                                show_down_arrow = False
                            elif count_right == 0:
                                show_right_arrow = True
                                show_down_arrow = False
                            elif count_below == 0:
                                show_down_arrow = True
                                show_right_arrow = False
                            elif count_above == 0:
                                show_down_arrow = True
                                show_right_arrow = False
                        elif self._is_one_or_two(count_above) and count_below == 0 and count_left == 0 and count_right == 0:
                            show_right_arrow = False
                            show_down_arrow = True
                        elif self._is_one_or_two(count_below) and count_above == 0 and count_left == 0 and count_right == 0:
                            show_right_arrow = False
                            show_down_arrow = True
                        elif self._is_one_or_two(count_left) and count_above == 0 and count_below == 0 and count_right == 0:
                            show_down_arrow = False
                            show_right_arrow = True
                        elif self._is_one_or_two(count_right) and count_above == 0 and count_below == 0 and count_left == 0:
                            show_down_arrow = False
                            show_right_arrow = True
                        
                        # Rule: Dark blue cells always have both x and y axis arrows
                        is_dark_blue = self.is_dark_blue_cell(row, col)
                        if is_dark_blue:
                            show_down_arrow = True
                            show_right_arrow = True
                        else:
                            # Rule: Remove arrows if more than 8 blocks away from nearest occupied or dark blue cell
                            dist_x = self.distance_to_nearest_occupied_or_dark_blue_x(row, col)
                            if dist_x > 8:
                                show_right_arrow = False
                            
                            dist_y = self.distance_to_nearest_occupied_or_dark_blue_y(row, col)
                            if dist_y > 8:
                                show_down_arrow = False
                        
                        down_arrows[row][col] = show_down_arrow
                        right_arrows[row][col] = show_right_arrow
        
        # Draw grid cells
        for row in range(N):
            for col in range(N):
                x, y = self.coord_to_pixel(row, col)
                cell_value = self.board[row][col]
                
                # Determine fill color
                fill_color = 'white'
                if cell_value == ' ' and self.is_adjacent_to_occupied(row, col):
                    # Check if any side has more than 2 contiguous adjacent blocks
                    count_above = self.count_contiguous_in_direction(row, col, -1, 0)  # up
                    count_below = self.count_contiguous_in_direction(row, col, 1, 0)   # down
                    count_left = self.count_contiguous_in_direction(row, col, 0, -1)   # left
                    count_right = self.count_contiguous_in_direction(row, col, 0, 1)   # right
                    
                    # If any side has more than 2, use darker blue
                    if count_above > 2 or count_below > 2 or count_left > 2 or count_right > 2:
                        fill_color = 'steel blue'  # Darker blue for >2 adjacent blocks
                    else:
                        fill_color = 'light blue'  # Normal light blue
                
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
                
        # Draw arrows (individual or long based on toggle)
        if self.show_arrows:
            if self.show_long_arrows:
                # Draw long arrows by finding contiguous groups
                # For down arrows: group by column, find contiguous rows
                for col in range(N):
                    start_row = None
                    for row in range(N):
                        if down_arrows[row][col]:
                            if start_row is None:
                                start_row = row
                        else:
                            if start_row is not None:
                                # Draw long arrow from start_row to row-1
                                self.draw_long_arrow_down(start_row, row - 1, col)
                                start_row = None
                    # Handle case where group extends to end
                    if start_row is not None:
                        self.draw_long_arrow_down(start_row, N - 1, col)
                
                # For right arrows: group by row, find contiguous columns
                for row in range(N):
                    start_col = None
                    for col in range(N):
                        if right_arrows[row][col]:
                            if start_col is None:
                                start_col = col
                        else:
                            if start_col is not None:
                                # Draw long arrow from start_col to col-1
                                self.draw_long_arrow_right(row, start_col, col - 1)
                                start_col = None
                    # Handle case where group extends to end
                    if start_col is not None:
                        self.draw_long_arrow_right(row, start_col, N - 1)
            else:
                # Draw individual arrows
                for row in range(N):
                    for col in range(N):
                        if down_arrows[row][col]:
                            x, y = self.coord_to_pixel(row, col)
                            arrow_size = CELL_SIZE * 0.5
                            self.draw_arrow_down(x, y, arrow_size)
                        if right_arrows[row][col]:
                            x, y = self.coord_to_pixel(row, col)
                            arrow_size = CELL_SIZE * 0.5
                            self.draw_arrow_right(x, y, arrow_size)
    
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

