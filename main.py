# main.py - SmoL Chess main loop with dynamic AI selection and live GUI stats.

import threading
import time

import pygame

from ai_fuzzy import FuzzyPlayer
from ai_mcts import MCTSPlayer
from ai_minimax import MinimaxPlayer
from board import apply_move, copy_board, create_board, find_king, get_legal_moves, is_checkmate, is_in_check
from game_rules import MatchDrawTracker, draw_reason
from gui import GUI
from pieces import King, Knight, Pawn, Queen

MAX_MOVES = 200
MOVE_DELAY_SEC = 0.25
THINK_POLL_MS = 50

OPTION_DEFS = {
    "minimax": {
        "title": "Minimax",
        "subtitle": "Alpha-beta tactical search",
        "type_label": "Minimax",
    },
    "mcts": {
        "title": "MCTS",
        "subtitle": "Monte Carlo tree search",
        "type_label": "MCTS",
    },
    "fuzzy": {
        "title": "Fuzzy Logic",
        "subtitle": "Deterministic Sugeno rules",
        "type_label": "Fuzzy",
    },
    "human": {
        "title": "Human",
        "subtitle": "Click pieces and legal target squares",
        "type_label": "Human",
    },
}


class HumanPlayer:
    is_human = True

    def __init__(self, color="W"):
        self.color = color
        self.name = "Human"

    def choose_move(self, board, draw_context=None):
        return None


PLAYER_BUILDERS = {
    "minimax": lambda color, max_time: MinimaxPlayer(color=color, depth=3, time_limit=max_time),
    "mcts": lambda color, max_time: MCTSPlayer(color=color, simulations=800, time_limit=max_time),
    "fuzzy": lambda color, max_time: FuzzyPlayer(color=color),
    "human": lambda color, max_time: HumanPlayer(color=color),
}


def piece_name(piece):
    names = {King: "King", Queen: "Queen", Knight: "Knight", Pawn: "Pawn"}
    return names.get(type(piece), "?")


def col_letter(col):
    return "abcdef"[col]


class AIWorker(threading.Thread):
    def __init__(self, player, board, draw_context=None):
        super().__init__(daemon=True)
        self.player = player
        self.board = copy_board(board)
        self.draw_context = draw_context
        self.result = None

    def run(self):
        self.result = self.player.choose_move(self.board, self.draw_context)


def wait_with_countdown(
    gui,
    board,
    status,
    move_num,
    last_move,
    check_king,
    current_turn,
    last_move_time,
    seconds=MOVE_DELAY_SEC,
):
    """
    Show a short visual pause after a move.
    Keeps pumping pygame events so the window stays responsive.
    """
    start = time.time()
    while True:
        elapsed = time.time() - start
        remaining = seconds - elapsed
        if remaining <= 0:
            break
        gui.update(
            board,
            status,
            move_num,
            last_move=last_move,
            check_king=check_king,
            current_turn=current_turn,
            last_move_time=last_move_time,
        )
        pygame.time.delay(80)


def build_players(selection, max_ai_time):
    white = PLAYER_BUILDERS[selection["W"]]("W", max_ai_time)
    black = PLAYER_BUILDERS[selection["B"]]("B", max_ai_time)
    return white, black


def fallback_move(board, color):
    legal = get_legal_moves(board, color)
    return legal[0] if legal else None


def move_key(move):
    if move is None:
        return None
    piece, dest = move
    return ((piece.row, piece.col), dest)


def resolve_current_legal_move(board, color, move):
    """
    Convert a move returned from a copied or stale search board into the
    matching legal move object on the current live board.
    """
    target_key = move_key(move)
    if target_key is None:
        return None

    for legal_piece, legal_dest in get_legal_moves(board, color):
        if ((legal_piece.row, legal_piece.col), legal_dest) == target_key:
            return legal_piece, legal_dest

    return None


def run_game():
    board = create_board()
    gui = GUI()

    selection = gui.show_start_menu(OPTION_DEFS, default_white="human", default_black="mcts")
    max_ai_time = selection.get("max_ai_time", 4.5)
    white, black = build_players(selection, max_ai_time)
    gui.set_match_players(
        white,
        black,
        OPTION_DEFS[selection["W"]]["type_label"],
        OPTION_DEFS[selection["B"]]["type_label"],
    )

    players = {"W": white, "B": black}
    current = "W"
    move_num = 0
    last_move_time = None
    last_move = None
    draw_tracker = MatchDrawTracker(board, current)

    gui.add_log("Game started!")
    gui.add_log(f"White: {white.name}")
    gui.add_log(f"Black: {black.name}")
    gui.add_log(f"AI max think time: {max_ai_time:.1f}s")
    gui.update(board, "Match ready", move_num, current_turn=current, last_move_time=last_move_time)

    while True:
        player = players[current]
        opponent = "B" if current == "W" else "W"
        color_name = "White" if current == "W" else "Black"

        if is_checkmate(board, current):
            winner = "White" if current == "B" else "Black"
            message = f"{winner} wins by Checkmate!"
            gui.add_log(f"CHECKMATE! {message}")
            gui.update(board, "Checkmate!", move_num, current_turn=current, last_move_time=last_move_time)
            pygame.time.delay(1000)
            gui.show_winner(message, board)
            return

        reason = draw_reason(board, current, draw_tracker.snapshot())
        if reason:
            message = f"Draw - {reason}!"
            gui.add_log(message)
            gui.update(
                board,
                reason,
                move_num,
                last_move=last_move,
                current_turn=current,
                last_move_time=last_move_time,
            )
            pygame.time.delay(1000)
            gui.show_winner(message, board)
            return

        if move_num >= MAX_MOVES:
            gui.add_log("Move limit - Draw!")
            gui.update(board, "Draw!", move_num, current_turn=current, last_move_time=last_move_time)
            pygame.time.delay(1000)
            gui.show_winner("Draw - Move Limit!", board)
            return

        in_check = is_in_check(board, current)
        check_king_pos = None
        if in_check:
            king = find_king(board, current)
            if king:
                check_king_pos = (king.row, king.col)

        if getattr(player, "is_human", False):
            result = gui.get_human_move(
                board,
                current,
                f"{color_name} to move",
                move_num,
                last_move=last_move,
                check_king=check_king_pos,
                current_turn=current,
                last_move_time=last_move_time,
            )
            last_move_time = None
        else:
            worker = AIWorker(player, board, draw_tracker.snapshot())
            think_start = time.time()
            worker.start()

            dot_chars = [".", "..", "...", "...."]
            dot_idx = 0
            while worker.is_alive():
                elapsed = time.time() - think_start
                if elapsed >= max_ai_time:
                    gui.add_log(f"{color_name} reached the {max_ai_time:.1f}s limit")
                    break
                spinner = dot_chars[dot_idx % len(dot_chars)]
                gui.update(
                    board,
                    f"{color_name} thinking{spinner}",
                    move_num,
                    last_move=last_move,
                    check_king=check_king_pos,
                    current_turn=current,
                    last_move_time=last_move_time,
                )
                pygame.time.delay(THINK_POLL_MS)
                dot_idx += 1

            last_move_time = min(time.time() - think_start, max_ai_time)
            result = worker.result if not worker.is_alive() else fallback_move(board, current)

        if result is None:
            gui.add_log(f"{color_name} has no moves - Draw!")
            gui.show_winner("Draw - No Moves!", board)
            return

        resolved = resolve_current_legal_move(board, current, result)
        if resolved is None:
            gui.add_log(f"{color_name} produced a stale move; using fallback")
            resolved = fallback_move(board, current)

        if resolved is None:
            gui.add_log(f"{color_name} has no legal fallback - Draw!")
            gui.show_winner("Draw - No Moves!", board)
            return

        result = resolved
        piece, dest = result
        r0, c0 = piece.row, piece.col
        r1, c1 = dest
        captured_piece = board[r1][c1]
        moved_was_pawn = isinstance(piece, Pawn)

        notation = (
            f"{'W' if current == 'W' else 'B'}"
            f"{move_num // 2 + 1}: "
            f"{piece_name(piece)} "
            f"{col_letter(c0)}{6-r0}->{col_letter(c1)}{6-r1}"
        )
        if in_check:
            notation += " (escapes check)"

        apply_move(board, piece, dest)
        draw_tracker.record_after_move(board, opponent, moved_was_pawn, captured_piece)
        move_num += 1
        last_move = ((r0, c0), (r1, c1))

        opp_in_check = is_in_check(board, opponent)
        if opp_in_check:
            notation += " +"
        gui.add_log(notation)

        opp_check_pos = None
        if opp_in_check:
            king = find_king(board, opponent)
            if king:
                opp_check_pos = (king.row, king.col)

        move_status = "Check!" if opp_in_check else f"{color_name} moved"
        wait_with_countdown(
            gui,
            board,
            status=move_status,
            move_num=move_num,
            last_move=last_move,
            check_king=opp_check_pos,
            current_turn=opponent,
            last_move_time=last_move_time,
            seconds=min(MOVE_DELAY_SEC, max_ai_time),
        )

        current = opponent


if __name__ == "__main__":
    run_game()
