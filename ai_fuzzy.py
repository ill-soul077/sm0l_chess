# ai_fuzzy.py — Player 2: Fuzzy Logic System

from board import get_legal_moves, apply_move, is_in_check, is_checkmate
from pieces import King, Queen, Knight, Pawn
import random

# ──────────────────────────────────────────────
# Fuzzification helpers
# ──────────────────────────────────────────────

def material_score(board, color):
    """Raw material count for color."""
    values = {Queen: 9, Knight: 3, Pawn: 1, King: 0}
    score = 0
    for row in board:
        for piece in row:
            if piece and piece.color == color:
                score += values.get(type(piece), 0)
    return score


def fuzzy_material_advantage(board, color):
    """
    Returns fuzzy membership: (low, medium, high)
    Advantage = my material - opponent material
    """
    opponent = 'B' if color == 'W' else 'W'
    diff = material_score(board, color) - material_score(board, opponent)

    if diff <= -3:
        return (1.0, 0.0, 0.0)   # Low
    elif diff <= 0:
        d = (diff + 3) / 3
        return (1-d, d, 0.0)
    elif diff <= 3:
        d = diff / 3
        return (0.0, 1-d, d)
    else:
        return (0.0, 0.0, 1.0)   # High


def fuzzy_king_danger(board, color):
    """
    Returns (safe, exposed) membership.
    Checks: is king in check? how many attackers?
    """
    opponent = 'B' if color == 'W' else 'W'
    in_check = is_in_check(board, color)

    # Count how many opponent pieces can reach king area
    king_pos = None
    for row in board:
        for piece in row:
            if isinstance(piece, King) and piece.color == color:
                king_pos = (piece.row, piece.col)

    if king_pos is None:
        return (0.0, 1.0)

    threats = 0
    for row in board:
        for piece in row:
            if piece and piece.color == opponent:
                moves = piece.get_moves(board)
                # Count moves near king
                for (r, c) in moves:
                    if abs(r - king_pos[0]) <= 1 and abs(c - king_pos[1]) <= 1:
                        threats += 1

    if in_check:
        return (0.0, 1.0)        # Fully exposed
    elif threats >= 3:
        return (0.2, 0.8)
    elif threats >= 1:
        return (0.6, 0.4)
    else:
        return (1.0, 0.0)        # Safe


def fuzzy_center_control(board, color):
    """
    Returns (weak, strong) membership based on center squares controlled.
    """
    CENTER = [(2,2),(2,3),(3,2),(3,3)]
    count = 0
    for row in board:
        for piece in row:
            if piece and piece.color == color:
                for (r, c) in piece.get_moves(board):
                    if (r, c) in CENTER:
                        count += 1

    if count == 0:
        return (1.0, 0.0)
    elif count <= 2:
        d = count / 2
        return (1-d, d)
    else:
        return (0.0, 1.0)


# ──────────────────────────────────────────────
# Move scorer using fuzzy rules
# ──────────────────────────────────────────────

def score_move(board, piece, dest, color):
    """
    Apply fuzzy inference to score a candidate move.
    Higher score = better move.
    """
    opponent = 'B' if color == 'W' else 'W'
    new_board = apply_move(board, piece, dest)

    mat_low, mat_med, mat_high = fuzzy_material_advantage(new_board, color)
    king_safe, king_exposed = fuzzy_king_danger(new_board, color)
    center_weak, center_strong = fuzzy_center_control(new_board, color)

    score = 0.0

    # Rule 1: IF King Danger is High THEN prioritize defensive moves
    # → heavy penalty if move leaves king exposed
    score -= king_exposed * 5.0

    # Rule 2: IF Material Advantage is High AND King is Safe THEN trade/simplify
    # → reward captures
    target = board[dest[0]][dest[1]]
    if target is not None:
        capture_values = {Queen: 9, Knight: 3, Pawn: 1, King: 100}
        capture_val = capture_values.get(type(target), 0)
        score += mat_high * 0.5 * capture_val   # trade when winning
        score += mat_low  * 1.5 * capture_val   # desperately grab material when losing

    # Rule 3: IF Center Control is Weak THEN favor moves increasing central presence
    score += center_weak * center_strong * 2.0   # if weak, bonus for improving it

    # Bonus: moving toward opponent's territory
    if color == 'B':
        score += dest[0] * 0.1
    else:
        score += (5 - dest[0]) * 0.1

    # Bonus: checking the opponent
    if is_in_check(new_board, opponent):
        score += 3.0

    # Bonus: checkmate
    if is_checkmate(new_board, opponent):
        score += 1000.0

    return score


class FuzzyPlayer:
    def __init__(self, color='B'):
        self.color = color
        self.name = "Fuzzy Logic"

    def choose_move(self, board):
        legal = get_legal_moves(board, self.color)
        if not legal:
            return None

        scored = []
        for piece, dest in legal:
            s = score_move(board, piece, dest, self.color)
            scored.append((s, piece, dest))

        scored.sort(key=lambda x: x[0], reverse=True)

        # Pick from top 3 with slight randomness for variety
        top_n = scored[:3]
        weights = [3, 2, 1][:len(top_n)]
        chosen = random.choices(top_n, weights=weights, k=1)[0]
        return (chosen[1], chosen[2])
