# ai_fuzzy.py - Formal Sugeno-style fuzzy logic player.

from board import apply_move, get_legal_moves, is_checkmate, is_in_check, undo_move
from pieces import King, Knight, Pawn, Queen

PIECE_VALUES = {
    King: 0,
    Queen: 9,
    Knight: 3,
    Pawn: 1,
}

CENTER = {(2, 2), (2, 3), (3, 2), (3, 3)}
VERY_BAD = 10.0
BAD = 30.0
NEUTRAL = 50.0
GOOD = 70.0
EXCELLENT = 90.0


def triangular(x, a, b, c):
    if x <= a or x >= c:
        return 0.0
    if x == b:
        return 1.0
    if x < b:
        return (x - a) / (b - a)
    return (c - x) / (c - b)


def trapezoidal(x, a, b, c, d):
    if x <= a or x >= d:
        return 0.0
    if b <= x <= c:
        return 1.0
    if x < b:
        return (x - a) / (b - a)
    return (d - x) / (d - c)


def material_total(board, color):
    return sum(
        PIECE_VALUES.get(type(piece), 0)
        for row in board
        for piece in row
        if piece and piece.color == color
    )


def material_advantage(board, color):
    opponent = "B" if color == "W" else "W"
    return material_total(board, color) - material_total(board, opponent)


def count_attackers(board, square, by_color):
    row_target, col_target = square
    total = 0
    for row in board:
        for piece in row:
            if piece and piece.color == by_color:
                if (row_target, col_target) in piece.get_moves(board):
                    total += 1
    return total


def find_king_square(board, color):
    for row in board:
        for piece in row:
            if isinstance(piece, King) and piece.color == color:
                return (piece.row, piece.col)
    return None


def king_danger_index(board, color):
    opponent = "B" if color == "W" else "W"
    king_square = find_king_square(board, color)
    if king_square is None:
        return 6.0

    threats = 0
    for row in board:
        for piece in row:
            if piece and piece.color == opponent:
                for dest_row, dest_col in piece.get_moves(board):
                    if abs(dest_row - king_square[0]) <= 1 and abs(dest_col - king_square[1]) <= 1:
                        threats += 1

    value = (2 if is_in_check(board, color) else 0) + threats
    return float(max(0, min(6, value)))


def center_control_count(board, color):
    controlled = set()
    for row in board:
        for piece in row:
            if piece and piece.color == color:
                for square in piece.get_moves(board):
                    if square in CENTER:
                        controlled.add(square)
    return float(len(controlled))


def fuzzy_material_sets(value):
    return {
        "disadvantaged": trapezoidal(value, -17, -17, -6, -1),
        "balanced": triangular(value, -3, 0, 3),
        "advantaged": trapezoidal(value, 1, 6, 17, 17),
    }


def fuzzy_king_danger_sets(value):
    return {
        "safe": trapezoidal(value, 0, 0, 0.5, 1.5),
        "warning": triangular(value, 1, 2, 3),
        "exposed": trapezoidal(value, 2.5, 3.5, 6, 6),
    }


def fuzzy_center_sets(value):
    return {
        "weak": trapezoidal(value, 0, 0, 0.5, 1.5),
        "moderate": triangular(value, 1, 2, 3),
        "strong": trapezoidal(value, 2.5, 3.5, 4, 4),
    }


def moved_piece_hanging(board, square, color):
    opponent = "B" if color == "W" else "W"
    return count_attackers(board, square, opponent) > 0 and count_attackers(board, square, color) == 0


def move_features(board, piece, dest, color):
    opponent = "B" if color == "W" else "W"
    before_adv = material_advantage(board, color)
    capture_target = board[dest[0]][dest[1]]
    undo = apply_move(board, piece, dest)

    check = is_in_check(board, opponent)
    mate = is_checkmate(board, opponent)
    promotion = isinstance(piece, Pawn) and ((piece.color == "W" and dest[0] == 0) or (piece.color == "B" and dest[0] == 5))
    features = {
        "pre_material_advantage": before_adv,
        "post_material_advantage": material_advantage(board, color),
        "king_danger_index": king_danger_index(board, color),
        "center_control_count": center_control_count(board, color),
        "capture_value": PIECE_VALUES.get(type(capture_target), 0) if capture_target is not None else 0,
        "gives_check": check,
        "gives_mate": mate,
        "promotion": promotion,
        "hanging": moved_piece_hanging(board, dest, color),
    }
    undo_move(board, undo)
    return features


def sugeno_score(features):
    material_sets = fuzzy_material_sets(features["post_material_advantage"])
    king_sets = fuzzy_king_danger_sets(features["king_danger_index"])
    center_sets = fuzzy_center_sets(features["center_control_count"])

    rules = []
    rules.append((king_sets["exposed"], VERY_BAD))
    rules.append((min(king_sets["safe"], material_sets["advantaged"]), GOOD))
    rules.append((min(material_sets["balanced"], center_sets["strong"]), GOOD))

    if features["post_material_advantage"] > features["pre_material_advantage"]:
        rules.append((material_sets["disadvantaged"], GOOD))

    rules.append((min(king_sets["warning"], center_sets["weak"]), BAD))
    rules.append((min(material_sets["advantaged"], center_sets["strong"]), EXCELLENT))
    rules.append((min(material_sets["balanced"], king_sets["safe"]), NEUTRAL))
    rules.append((min(material_sets["disadvantaged"], king_sets["safe"]), NEUTRAL))

    numerator = 0.0
    denominator = 0.0
    for strength, singleton in rules:
        if strength <= 0:
            continue
        numerator += strength * singleton
        denominator += strength

    if denominator == 0:
        return NEUTRAL
    return numerator / denominator


def score_move(board, piece, dest, color):
    features = move_features(board, piece, dest, color)
    score = sugeno_score(features)

    if features["gives_check"]:
        score += 8.0
    if features["hanging"]:
        score -= 12.0
    if features["promotion"]:
        score += 10.0
    if features["capture_value"] > 0:
        score += 2.0 * features["capture_value"]
    if features["gives_mate"]:
        score = 10000.0

    return score, features


def tie_break_key(dest, features):
    return (
        1 if features["gives_mate"] else 0,
        1 if features["promotion"] else 0,
        features["capture_value"],
        1 if features["gives_check"] else 0,
        -dest[1],
        -(6 - dest[0]),
    )


class FuzzyPlayer:
    def __init__(self, color="B"):
        self.color = color
        self.name = "Fuzzy Logic"

    def choose_move(self, board):
        legal = get_legal_moves(board, self.color)
        if not legal:
            return None

        best_entry = None
        for piece, dest in legal:
            score, features = score_move(board, piece, dest, self.color)
            key = tie_break_key(dest, features)
            entry = (score, key, piece, dest)
            if best_entry is None:
                best_entry = entry
                continue
            if score > best_entry[0]:
                best_entry = entry
                continue
            if score == best_entry[0] and key > best_entry[1]:
                best_entry = entry

        return (best_entry[2], best_entry[3])
