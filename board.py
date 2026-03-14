# board.py — SmoL Chess Board (6x6)

from pieces import King, Queen, Knight, Pawn
import copy


def create_board():
    """
    ALL 6 pieces in a SINGLE back row each — no separate pawn row.

      col:   0      1       2      3      4       5
    Black:  Pawn  Knight  Queen  King  Knight   Pawn    row 0
    White:  Pawn  Knight  Queen  King  Knight   Pawn    row 5

    Rows 1-4 are empty at the start.
    """
    board = [[None]*6 for _ in range(6)]

    # --- Black pieces (Player 2 / Fuzzy Logic) — row 0 ---
    board[0][0] = Pawn  ('B', 0, 0)
    board[0][1] = Knight('B', 0, 1)
    board[0][2] = Queen ('B', 0, 2)
    board[0][3] = King  ('B', 0, 3)
    board[0][4] = Knight('B', 0, 4)
    board[0][5] = Pawn  ('B', 0, 5)

    # --- White pieces (Player 1 / Minimax) — row 5 ---
    board[5][0] = Pawn  ('W', 5, 0)
    board[5][1] = Knight('W', 5, 1)
    board[5][2] = Queen ('W', 5, 2)
    board[5][3] = King  ('W', 5, 3)
    board[5][4] = Knight('W', 5, 4)
    board[5][5] = Pawn  ('W', 5, 5)

    return board


def get_all_moves(board, color):
    """Return list of (piece, (to_row, to_col)) for all legal moves of color."""
    moves = []
    for row in board:
        for piece in row:
            if piece and piece.color == color:
                for dest in piece.get_moves(board):
                    moves.append((piece, dest))
    return moves


def apply_move(board, piece, dest):
    """
    Apply a move to a COPY of the board and return new board.
    Handles pawn promotion and has_moved flag.
    """
    new_board = copy.deepcopy(board)
    r0, c0 = piece.row, piece.col
    r1, c1 = dest

    moving = new_board[r0][c0]
    new_board[r0][c0] = None
    new_board[r1][c1] = moving
    moving.row, moving.col = r1, c1

    # Mark pawn as moved
    if isinstance(moving, Pawn):
        moving.has_moved = True
        # Pawn promotion → Queen
        if (moving.color == 'W' and r1 == 0) or (moving.color == 'B' and r1 == 5):
            new_board[r1][c1] = Queen(moving.color, r1, c1)

    return new_board


def find_king(board, color):
    for row in board:
        for piece in row:
            if isinstance(piece, King) and piece.color == color:
                return piece
    return None


def is_in_check(board, color):
    """Return True if `color`'s king is under attack."""
    king = find_king(board, color)
    if king is None:
        return True   # king captured → losing state
    opponent = 'B' if color == 'W' else 'W'
    for row in board:
        for piece in row:
            if piece and piece.color == opponent:
                if (king.row, king.col) in piece.get_moves(board):
                    return True
    return False


def get_legal_moves(board, color):
    """Return only moves that don't leave own king in check."""
    legal = []
    for piece, dest in get_all_moves(board, color):
        new_board = apply_move(board, piece, dest)
        if not is_in_check(new_board, color):
            legal.append((piece, dest))
    return legal


def is_checkmate(board, color):
    return is_in_check(board, color) and len(get_legal_moves(board, color)) == 0


def is_stalemate(board, color):
    return not is_in_check(board, color) and len(get_legal_moves(board, color)) == 0


def print_board(board):
    """ASCII print for debugging."""
    print("  " + " ".join(str(c) for c in range(6)))
    for r, row in enumerate(board):
        line = f"{r} "
        for piece in row:
            line += (str(piece) if piece else " .") + " "
        print(line)
    print()