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
                
                # Draw cell rectangle
                self.canvas.create_rectangle(
                    x, y,
                    x + CELL_SIZE, y + CELL_SIZE,
                    fill='white',
                    outline='black',
                    width=1
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
