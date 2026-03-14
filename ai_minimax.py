# ai_minimax.py — Player 1: Minimax + Alpha-Beta Pruning (depth 5)

from board import get_legal_moves, apply_move, is_checkmate, is_stalemate, is_in_check
from pieces import King, Queen, Knight, Pawn
import math

# ──────────────────────────────────────────────
# Evaluation function
# ──────────────────────────────────────────────

PIECE_VALUES = {
    King:   10000,
    Queen:  9,
    Knight: 3,
    Pawn:   1,
}

# Centre squares on 6x6: cols 2-3, rows 2-3
CENTER = {(2,2),(2,3),(3,2),(3,3)}

def evaluate(board, color):
    """
    Positive score = good for `color`.
    Components:
      1. Material balance
      2. Mobility (legal move count difference)
      3. Center control
      4. King safety (penalty if in check)
    """
    opponent = 'B' if color == 'W' else 'W'
    score = 0

    my_mobility = len(get_legal_moves(board, color))
    opp_mobility = len(get_legal_moves(board, opponent))

    for row in board:
        for piece in row:
            if piece is None:
                continue
            val = PIECE_VALUES.get(type(piece), 0)
            sign = 1 if piece.color == color else -1
            score += sign * val

            # Center control bonus
            if (piece.row, piece.col) in CENTER:
                score += sign * 0.3

    # Mobility
    score += 0.1 * (my_mobility - opp_mobility)

    # King safety
    if is_in_check(board, color):
        score -= 2
    if is_in_check(board, opponent):
        score += 2

    return score


# ──────────────────────────────────────────────
# Minimax with Alpha-Beta Pruning
# ──────────────────────────────────────────────

def minimax(board, depth, alpha, beta, maximizing, my_color):
    opponent = 'B' if my_color == 'W' else 'W'
    current_color = my_color if maximizing else opponent

    # Terminal checks
    if is_checkmate(board, current_color):
        # current player is in checkmate → bad for them
        return (-math.inf if maximizing else math.inf), None

    if is_stalemate(board, current_color):
        return 0, None

    if depth == 0:
        return evaluate(board, my_color), None

    legal = get_legal_moves(board, current_color)
    if not legal:
        return evaluate(board, my_color), None

    best_move = None

    if maximizing:
        max_eval = -math.inf
        for piece, dest in legal:
            new_board = apply_move(board, piece, dest)
            eval_score, _ = minimax(new_board, depth-1, alpha, beta, False, my_color)
            if eval_score > max_eval:
                max_eval = eval_score
                best_move = (piece, dest)
            alpha = max(alpha, eval_score)
            if beta <= alpha:
                break   # prune
        return max_eval, best_move
    else:
        min_eval = math.inf
        for piece, dest in legal:
            new_board = apply_move(board, piece, dest)
            eval_score, _ = minimax(new_board, depth-1, alpha, beta, True, my_color)
            if eval_score < min_eval:
                min_eval = eval_score
                best_move = (piece, dest)
            beta = min(beta, eval_score)
            if beta <= alpha:
                break   # prune
        return min_eval, best_move


class MinimaxPlayer:
    def __init__(self, color='W', depth=3):
        self.color = color
        self.depth = depth
        self.name = "Minimax (α-β)"

    def choose_move(self, board):
        _, best = minimax(board, self.depth, -math.inf, math.inf, True, self.color)
        return best