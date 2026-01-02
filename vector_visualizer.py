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
            text="Click tiles to mark them. Green = valid, Red = invalid, Arrows show valid vectors",
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
    
    def compute_cell_states(self, valid_vectors: List[Vector]) -> List[List[str]]:
        """
        Compute cell states for all cells based on valid vectors.
        Returns a 15x15 grid of states: 'marked', 'valid', or 'invalid'
        """
        states = [['invalid' for _ in range(N)] for _ in range(N)]
        
        # Mark all cells with tiles as 'marked'
        for row in range(N):
            for col in range(N):
                if self.board[row][col] != ' ':
                    states[row][col] = 'marked'
        
        # Mark cells on valid vectors as 'valid' (but not if already marked)
        for vector in valid_vectors:
            if vector.is_horizontal:
                row = vector.start_row
                for col in range(vector.start_col, vector.end_col + 1):
                    if states[row][col] != 'marked':
                        states[row][col] = 'valid'
            else:
                col = vector.start_col
                for row in range(vector.start_row, vector.end_row + 1):
                    if states[row][col] != 'marked':
                        states[row][col] = 'valid'
        
        return states
    
    def redraw(self):
        """Redraw the entire grid"""
        self.canvas.delete("all")
        
        # Get valid vectors once
        valid_vectors = generate_valid_vectors(self.board)
        
        # Compute all cell states
        cell_states = self.compute_cell_states(valid_vectors)
        
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
                else:  # invalid
                    fill_color = 'lightcoral'
                
                # Highlight center square
                if (row, col) == CENTER_SQUARE and state != 'marked':
                    if fill_color == 'lightcoral':
                        fill_color = '#FFB6C1'  # Light pink for invalid center
                    elif fill_color == 'lightgreen':
                        fill_color = '#90EE90'  # Slightly brighter green
                
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
        
        # Draw arrows for valid vectors (through green cells)
        for vector in valid_vectors:
            self.draw_vector_arrow(vector)
        
        # Update status
        marked_count = sum(1 for row in self.board for cell in row if cell != ' ')
        self.status_label.config(
            text=f"Marked: {marked_count} | Valid vectors: {len(valid_vectors)} | Click tiles to mark/unmark"
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

