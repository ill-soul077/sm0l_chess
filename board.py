# board.py - SmoL Chess Board (6x6)
#
# This board engine intentionally has no castling and no en-passant.
# The apply/undo token only stores the state needed for this rule set.

from pieces import King, Knight, Pawn, Queen


def create_board():
    """
    All 6 pieces start in a single back row for each side.

      col:   0      1       2      3      4       5
    Black:  Pawn  Knight  Queen  King  Knight   Pawn    row 0
    White:  Pawn  Knight  Queen  King  Knight   Pawn    row 5

    Rows 1-4 are empty at the start.
    """
    board = [[None] * 6 for _ in range(6)]

    board[0][0] = Pawn("B", 0, 0)
    board[0][1] = Knight("B", 0, 1)
    board[0][2] = Queen("B", 0, 2)
    board[0][3] = King("B", 0, 3)
    board[0][4] = Knight("B", 0, 4)
    board[0][5] = Pawn("B", 0, 5)

    board[5][0] = Pawn("W", 5, 0)
    board[5][1] = Knight("W", 5, 1)
    board[5][2] = Queen("W", 5, 2)
    board[5][3] = King("W", 5, 3)
    board[5][4] = Knight("W", 5, 4)
    board[5][5] = Pawn("W", 5, 5)

    return board


def copy_piece(piece):
    if piece is None:
        return None

    copied = type(piece)(piece.color, piece.row, piece.col)
    if isinstance(piece, Pawn):
        copied.has_moved = piece.has_moved
    return copied


def copy_board(board):
    """
    Create an explicit board snapshot.

    This is the approved way to create an independent board copy for
    persistent states such as MCTS tree nodes.
    """
    new_board = [[None] * 6 for _ in range(6)]
    for row in range(6):
        for col in range(6):
            piece = board[row][col]
            if piece is not None:
                new_board[row][col] = copy_piece(piece)
    return new_board


def get_all_moves(board, color):
    """Return list of (piece, (to_row, to_col)) for all pseudo-legal moves."""
    moves = []
    for row in board:
        for piece in row:
            if piece and piece.color == color:
                for dest in piece.get_moves(board):
                    moves.append((piece, dest))
    return moves


def apply_move(board, piece, dest):
    """
    Apply a move in place and return an undo token.

    The undo token is intentionally minimal because this mini-chess variant
    has no castling and no en-passant.
    """
    r0, c0 = piece.row, piece.col
    r1, c1 = dest

    moving = board[r0][c0]
    captured = board[r1][c1]
    previous_has_moved = getattr(moving, "has_moved", None)

    board[r0][c0] = None
    board[r1][c1] = moving
    moving.row, moving.col = r1, c1

    promoted_piece = None
    if isinstance(moving, Pawn):
        moving.has_moved = True
        if (moving.color == "W" and r1 == 0) or (moving.color == "B" and r1 == 5):
            promoted_piece = Queen(moving.color, r1, c1)
            board[r1][c1] = promoted_piece

    return {
        "piece": moving,
        "src": (r0, c0),
        "dst": (r1, c1),
        "captured": captured,
        "previous_has_moved": previous_has_moved,
        "promoted_piece": promoted_piece,
    }


def undo_move(board, undo_token):
    """Undo a move previously applied by apply_move()."""
    r0, c0 = undo_token["src"]
    r1, c1 = undo_token["dst"]
    moving = undo_token["piece"]
    captured = undo_token["captured"]
    promoted_piece = undo_token["promoted_piece"]

    board[r1][c1] = captured
    board[r0][c0] = moving
    moving.row, moving.col = r0, c0

    if isinstance(moving, Pawn):
        moving.has_moved = undo_token["previous_has_moved"]

    if promoted_piece is not None:
        board[r1][c1] = captured
        board[r0][c0] = moving

    if captured is not None:
        captured.row, captured.col = r1, c1


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
        return True

    opponent = "B" if color == "W" else "W"
    for row in board:
        for piece in row:
            if piece and piece.color == opponent:
                if (king.row, king.col) in piece.get_moves(board):
                    return True
    return False


def get_legal_moves(board, color):
    """Return only moves that do not leave the moving side in check."""
    legal = []
    for piece, dest in get_all_moves(board, color):
        undo = apply_move(board, piece, dest)
        if not is_in_check(board, color):
            legal.append((piece, dest))
        undo_move(board, undo)
    return legal


def is_checkmate(board, color):
    return is_in_check(board, color) and len(get_legal_moves(board, color)) == 0


def is_stalemate(board, color):
    return not is_in_check(board, color) and len(get_legal_moves(board, color)) == 0


def print_board(board):
    """ASCII print for debugging."""
    print("  " + " ".join(str(c) for c in range(6)))
    for row_idx, row in enumerate(board):
        line = f"{row_idx} "
        for piece in row:
            line += (str(piece) if piece else " .") + " "
        print(line)
    print()
