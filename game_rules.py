# game_rules.py - Match-level draw rules for SmoL Chess.

from dataclasses import dataclass

from board import apply_move, is_stalemate, undo_move
from pieces import King, Knight, Pawn, Queen

THREEFOLD_REPETITION_COUNT = 3
FIFTY_MOVE_HALFMOVES = 100

PIECE_CODES = {
    King: "K",
    Queen: "Q",
    Knight: "N",
    Pawn: "P",
}


@dataclass(frozen=True)
class DrawContext:
    position_counts: dict
    halfmove_clock: int = 0


def opponent_of(color):
    return "B" if color == "W" else "W"


def copy_draw_context(context):
    if context is None:
        return None
    return DrawContext(dict(context.position_counts), context.halfmove_clock)


def board_position_key(board, side_to_move):
    """
    Position identity for repetition.

    SmoL Chess has no castling or en-passant, but pawn first-move rights affect
    legal moves, so pawn has_moved state is part of the key.
    """
    entries = [side_to_move]
    for row in range(6):
        for col in range(6):
            piece = board[row][col]
            if piece is None:
                continue
            code = PIECE_CODES.get(type(piece), "?")
            moved = "1" if getattr(piece, "has_moved", False) else "0"
            entries.append(f"{piece.color}{code}{row}{col}{moved}")
    return "|".join(entries)


def has_mating_material(board, color):
    minor_count = 0
    for row in board:
        for piece in row:
            if piece is None or piece.color != color:
                continue
            if isinstance(piece, (Queen, Pawn)):
                return True
            if isinstance(piece, Knight):
                minor_count += 1
    return minor_count >= 2


def is_insufficient_material(board):
    return not has_mating_material(board, "W") and not has_mating_material(board, "B")


def next_halfmove_clock(context, moved_was_pawn, captured_piece):
    if context is None:
        return 0
    if moved_was_pawn or captured_piece is not None:
        return 0
    return context.halfmove_clock + 1


def advance_context_after_move(context, board, side_to_move, moved_was_pawn, captured_piece):
    if context is None:
        return None

    counts = dict(context.position_counts)
    key = board_position_key(board, side_to_move)
    counts[key] = counts.get(key, 0) + 1
    return DrawContext(
        counts,
        next_halfmove_clock(context, moved_was_pawn, captured_piece),
    )


def draw_reason(board, side_to_move, context=None):
    if is_stalemate(board, side_to_move):
        return "Stalemate"
    if is_insufficient_material(board):
        return "Insufficient material"
    if context is None:
        return None
    if context.halfmove_clock >= FIFTY_MOVE_HALFMOVES:
        return "50-move rule"

    key = board_position_key(board, side_to_move)
    if context.position_counts.get(key, 0) >= THREEFOLD_REPETITION_COUNT:
        return "Threefold repetition"

    return None


def draw_reason_after_move(board, piece, dest, color, context=None):
    opponent = opponent_of(color)
    captured_piece = board[dest[0]][dest[1]]
    moved_was_pawn = isinstance(piece, Pawn)

    undo = apply_move(board, piece, dest)
    next_context = advance_context_after_move(
        context,
        board,
        opponent,
        moved_was_pawn,
        captured_piece,
    )
    reason = draw_reason(board, opponent, next_context)
    undo_move(board, undo)
    return reason


class MatchDrawTracker:
    def __init__(self, board, side_to_move):
        key = board_position_key(board, side_to_move)
        self.context = DrawContext({key: 1}, 0)

    def snapshot(self):
        return copy_draw_context(self.context)

    def record_after_move(self, board, side_to_move, moved_was_pawn, captured_piece):
        self.context = advance_context_after_move(
            self.context,
            board,
            side_to_move,
            moved_was_pawn,
            captured_piece,
        )
