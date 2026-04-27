# ai_minimax.py - Minimax player with alpha-beta pruning, move ordering,
# and a Zobrist-hash transposition table.

import math
import random
import time

from board import apply_move, get_legal_moves, is_checkmate, is_in_check, undo_move
from game_rules import advance_context_after_move, draw_reason, opponent_of
from pieces import King, Knight, Pawn, Queen

PIECE_VALUES = {
    King: 10000,
    Queen: 9,
    Knight: 3,
    Pawn: 1,
}

CENTER = {(2, 2), (2, 3), (3, 2), (3, 3)}
TT_EXACT = "EXACT"
TT_LOWERBOUND = "LOWERBOUND"
TT_UPPERBOUND = "UPPERBOUND"
ZOBRIST_SEED = 20260423


class SearchTimeout(Exception):
    pass


def move_key(piece, dest):
    return ((piece.row, piece.col), dest)


def lookup_move(legal_moves, key):
    if key is None:
        return None
    for piece, dest in legal_moves:
        if move_key(piece, dest) == key:
            return (piece, dest)
    return None


def evaluate(board, color):
    """
    Positive score = good for `color`.
    Components:
      1. Material balance
      2. Mobility (legal move count difference)
      3. Center control
      4. King safety (penalty if in check)
    """
    opponent = "B" if color == "W" else "W"
    score = 0.0

    my_mobility = len(get_legal_moves(board, color))
    opp_mobility = len(get_legal_moves(board, opponent))

    for row in board:
        for piece in row:
            if piece is None:
                continue
            val = PIECE_VALUES.get(type(piece), 0)
            sign = 1 if piece.color == color else -1
            score += sign * val

            if (piece.row, piece.col) in CENTER:
                score += sign * 0.3

    score += 0.1 * (my_mobility - opp_mobility)

    if is_in_check(board, color):
        score -= 2
    if is_in_check(board, opponent):
        score += 2

    return score


def _build_zobrist_table():
    rng = random.Random(ZOBRIST_SEED)
    table = {}
    piece_names = ("King", "Queen", "Knight", "Pawn")

    for row in range(6):
        for col in range(6):
            for color in ("W", "B"):
                for piece_name in piece_names:
                    for pawn_moved in (False, True):
                        table[(row, col, color, piece_name, pawn_moved)] = rng.getrandbits(64)

    side_to_move = {
        "W": rng.getrandbits(64),
        "B": rng.getrandbits(64),
    }
    return table, side_to_move


ZOBRIST_TABLE, ZOBRIST_SIDE = _build_zobrist_table()


def zobrist_hash(board, side_to_move):
    h = ZOBRIST_SIDE[side_to_move]
    for row in board:
        for piece in row:
            if piece is None:
                continue
            pawn_moved = bool(getattr(piece, "has_moved", False))
            key = (piece.row, piece.col, piece.color, type(piece).__name__, pawn_moved)
            h ^= ZOBRIST_TABLE[key]
    return h


def draw_context_key(draw_context):
    if draw_context is None:
        return None
    return (
        draw_context.halfmove_clock,
        tuple(sorted(draw_context.position_counts.items())),
    )


def score_move(board, piece, dest, color):
    opponent = "B" if color == "W" else "W"
    target = board[dest[0]][dest[1]]
    undo = apply_move(board, piece, dest)
    score = 0.0

    if is_checkmate(board, opponent):
        score += 100000.0

    if isinstance(piece, Pawn) and ((piece.color == "W" and dest[0] == 0) or (piece.color == "B" and dest[0] == 5)):
        score += 2500.0

    if target is not None:
        victim = PIECE_VALUES.get(type(target), 0)
        attacker = PIECE_VALUES.get(type(piece), 0)
        score += 400.0 + (victim * 20.0) - attacker

    if is_in_check(board, opponent):
        score += 300.0

    if dest in CENTER:
        score += 25.0

    undo_move(board, undo)
    return score


def order_moves(board, legal_moves, color, preferred_move=None):
    ordered = []
    for piece, dest in legal_moves:
        key = move_key(piece, dest)
        priority = score_move(board, piece, dest, color)
        if preferred_move is not None and key == preferred_move:
            priority += 1000000.0
        ordered.append((priority, piece.row, piece.col, dest[0], dest[1], piece, dest))

    ordered.sort(key=lambda item: item[:5], reverse=True)
    return [(piece, dest) for _, _, _, _, _, piece, dest in ordered]


def _terminal_score(board, current_color, maximizing, draw_context=None):
    if is_checkmate(board, current_color):
        return (-math.inf if maximizing else math.inf), None
    if draw_reason(board, current_color, draw_context):
        return 0.0, None
    return None


def minimax(board, depth, alpha, beta, maximizing, my_color, player, ply=0, draw_context=None):
    if player._deadline is not None and time.monotonic() >= player._deadline:
        raise SearchTimeout

    player._stats["nodes"] += 1
    player._stats["max_depth"] = max(player._stats["max_depth"], ply)

    opponent = opponent_of(my_color)
    current_color = my_color if maximizing else opponent

    terminal = _terminal_score(board, current_color, maximizing, draw_context)
    if terminal is not None:
        return terminal

    if depth == 0:
        return evaluate(board, my_color), None

    board_hash = (zobrist_hash(board, current_color), draw_context_key(draw_context))
    original_alpha = alpha
    original_beta = beta
    tt_entry = player._tt.get(board_hash)
    tt_move_key = None

    if tt_entry is not None:
        tt_move_key = tt_entry.get("best_move")
        if tt_move_key is not None:
            player._stats["tt_ordering_hits"] += 1

        same_search = tt_entry.get("search_turn_id") == player._search_turn_id
        if same_search and tt_entry.get("depth", -1) >= depth:
            player._stats["tt_hits"] += 1
            flag = tt_entry["flag"]
            if flag == TT_EXACT:
                legal = get_legal_moves(board, current_color)
                return tt_entry["score"], lookup_move(legal, tt_move_key)
            if flag == TT_LOWERBOUND:
                alpha = max(alpha, tt_entry["score"])
            elif flag == TT_UPPERBOUND:
                beta = min(beta, tt_entry["score"])
            if alpha >= beta:
                legal = get_legal_moves(board, current_color)
                return tt_entry["score"], lookup_move(legal, tt_move_key)

    legal = get_legal_moves(board, current_color)
    if not legal:
        return evaluate(board, my_color), None

    legal = order_moves(board, legal, current_color, preferred_move=tt_move_key)
    best_move = None

    if maximizing:
        best_score = -math.inf
        for piece, dest in legal:
            captured = board[dest[0]][dest[1]]
            moved_was_pawn = isinstance(piece, Pawn)
            undo = apply_move(board, piece, dest)
            next_context = advance_context_after_move(
                draw_context,
                board,
                opponent_of(current_color),
                moved_was_pawn,
                captured,
            )
            score, _ = minimax(
                board,
                depth - 1,
                alpha,
                beta,
                False,
                my_color,
                player,
                ply + 1,
                next_context,
            )
            undo_move(board, undo)
            if score > best_score:
                best_score = score
                best_move = (piece, dest)
            alpha = max(alpha, best_score)
            if beta <= alpha:
                player._stats["cutoffs"] += 1
                break
    else:
        best_score = math.inf
        for piece, dest in legal:
            captured = board[dest[0]][dest[1]]
            moved_was_pawn = isinstance(piece, Pawn)
            undo = apply_move(board, piece, dest)
            next_context = advance_context_after_move(
                draw_context,
                board,
                opponent_of(current_color),
                moved_was_pawn,
                captured,
            )
            score, _ = minimax(
                board,
                depth - 1,
                alpha,
                beta,
                True,
                my_color,
                player,
                ply + 1,
                next_context,
            )
            undo_move(board, undo)
            if score < best_score:
                best_score = score
                best_move = (piece, dest)
            beta = min(beta, best_score)
            if beta <= alpha:
                player._stats["cutoffs"] += 1
                break

    if best_score <= original_alpha:
        flag = TT_UPPERBOUND
    elif best_score >= original_beta:
        flag = TT_LOWERBOUND
    else:
        flag = TT_EXACT

    player._tt[board_hash] = {
        "depth": depth,
        "score": best_score,
        "flag": flag,
        "best_move": move_key(*best_move) if best_move is not None else None,
        "search_turn_id": player._search_turn_id,
    }

    return best_score, best_move


class MinimaxPlayer:
    def __init__(self, color="W", depth=3, time_limit=4.5):
        self.color = color
        self.depth = depth
        self.time_limit = time_limit
        self.name = "Minimax (alpha-beta)"
        self.last_search_stats = {}
        self._tt = {}
        self._search_turn_id = 0
        self._stats = {}
        self._deadline = None

    def choose_move(self, board, draw_context=None):
        self._search_turn_id += 1
        self._deadline = None if self.time_limit is None else time.monotonic() + self.time_limit
        self._stats = {
            "nodes": 0,
            "cutoffs": 0,
            "tt_hits": 0,
            "tt_ordering_hits": 0,
            "max_depth": 0,
        }
        best = None
        try:
            for depth in range(1, self.depth + 1):
                _, candidate = minimax(
                    board,
                    depth,
                    -math.inf,
                    math.inf,
                    True,
                    self.color,
                    self,
                    ply=0,
                    draw_context=draw_context,
                )
                if candidate is not None:
                    best = candidate
        except SearchTimeout:
            pass
        finally:
            self._deadline = None

        if best is None:
            legal = get_legal_moves(board, self.color)
            if legal:
                best = order_moves(board, legal, self.color)[0]

        self.last_search_stats = dict(self._stats)
        return best
