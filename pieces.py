# pieces.py — SmoL Chess Piece Definitions
# Board is 6x6. Rows 0-5, Cols 0-5.
# Player 1 (Minimax) = 'W' (white), moves UP (decreasing row)
# Player 2 (Fuzzy)   = 'B' (black), moves DOWN (increasing row)

class Piece:
    def __init__(self, color, row, col):
        self.color = color      # 'W' or 'B'
        self.row = row
        self.col = col
        self.symbol = '?'

    def opponent(self):
        return 'B' if self.color == 'W' else 'W'

    def in_bounds(self, r, c):
        return 0 <= r < 6 and 0 <= c < 6

    def get_moves(self, board):
        raise NotImplementedError

    def __repr__(self):
        return f"{self.color}{self.symbol}"


class King(Piece):
    def __init__(self, color, row, col):
        super().__init__(color, row, col)
        self.symbol = 'K'
        self.value = 10000

    def get_moves(self, board):
        moves = []
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0:
                    continue
                r, c = self.row + dr, self.col + dc
                if self.in_bounds(r, c):
                    target = board[r][c]
                    if target is None or target.color == self.opponent():
                        moves.append((r, c))
        return moves


class Queen(Piece):
    """
    Range-limited queen: moves up to 2 squares in any direction
    (horizontal, vertical, or diagonal).
    """
    def __init__(self, color, row, col):
        super().__init__(color, row, col)
        self.symbol = 'Q'
        self.value = 9

    def get_moves(self, board):
        moves = []
        directions = [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]
        for dr, dc in directions:
            for step in range(1, 3):   # max 2 squares
                r, c = self.row + dr * step, self.col + dc * step
                if not self.in_bounds(r, c):
                    break
                target = board[r][c]
                if target is None:
                    moves.append((r, c))
                elif target.color == self.opponent():
                    moves.append((r, c))
                    break   # blocked after capture
                else:
                    break   # blocked by own piece
        return moves


class Knight(Piece):
    def __init__(self, color, row, col):
        super().__init__(color, row, col)
        self.symbol = 'N'
        self.value = 3

    def get_moves(self, board):
        moves = []
        offsets = [(-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)]
        for dr, dc in offsets:
            r, c = self.row + dr, self.col + dc
            if self.in_bounds(r, c):
                target = board[r][c]
                if target is None or target.color == self.opponent():
                    moves.append((r, c))
        return moves


class Pawn(Piece):
    """
    Pawns start on the back row alongside all other pieces.
    - Move 1 or 2 squares forward on first move (has_moved=False)
    - Move 1 square forward after that
    - Capture diagonally forward only
    - Promote to Queen on reaching the last row
    White moves UP (row decreases), Black moves DOWN (row increases).
    """
    def __init__(self, color, row, col):
        super().__init__(color, row, col)
        self.symbol   = 'P'
        self.value    = 1
        self.has_moved = False

    def direction(self):
        return -1 if self.color == 'W' else 1

    def get_moves(self, board):
        moves = []
        d = self.direction()

        # One step forward
        r, c = self.row + d, self.col
        if self.in_bounds(r, c) and board[r][c] is None:
            moves.append((r, c))
            # Two steps forward on first move (only if one-step square is clear)
            if not self.has_moved:
                r2, c2 = self.row + 2*d, self.col
                if self.in_bounds(r2, c2) and board[r2][c2] is None:
                    moves.append((r2, c2))

        # Diagonal captures
        for dc in [-1, 1]:
            r, c = self.row + d, self.col + dc
            if self.in_bounds(r, c):
                target = board[r][c]
                if target is not None and target.color == self.opponent():
                    moves.append((r, c))
        return moves