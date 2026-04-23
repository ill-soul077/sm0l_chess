# main.py - SmoL Chess main loop with dynamic AI selection and live GUI stats.

import threading
import time

import pygame

from ai_fuzzy import FuzzyPlayer
from ai_mcts import MCTSPlayer
from ai_minimax import MinimaxPlayer
from board import apply_move, copy_board, create_board, find_king, is_checkmate, is_in_check, is_stalemate
from gui import GUI
from pieces import King, Knight, Pawn, Queen

MAX_MOVES = 200
MOVE_DELAY_SEC = 5.0
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
}

PLAYER_BUILDERS = {
    "minimax": lambda color: MinimaxPlayer(color=color, depth=3),
    "mcts": lambda color: MCTSPlayer(color=color, simulations=800),
    "fuzzy": lambda color: FuzzyPlayer(color=color),
}


def piece_name(piece):
    names = {King: "King", Queen: "Queen", Knight: "Knight", Pawn: "Pawn"}
    return names.get(type(piece), "?")


def col_letter(col):
    return "abcdef"[col]


class AIWorker(threading.Thread):
    def __init__(self, player, board):
        super().__init__(daemon=True)
        self.player = player
        self.board = copy_board(board)
        self.result = None

    def run(self):
        self.result = self.player.choose_move(self.board)


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
    Show a live countdown on the GUI while the game pauses between moves.
    Keeps pumping pygame events so the window stays responsive.
    """
    start = time.time()
    while True:
        elapsed = time.time() - start
        remaining = seconds - elapsed
        if remaining <= 0:
            break
        countdown_status = f"{status} [{remaining:.1f}s]"
        gui.update(
            board,
            countdown_status,
            move_num,
            last_move=last_move,
            check_king=check_king,
            current_turn=current_turn,
            last_move_time=last_move_time,
        )
        pygame.time.delay(80)


def build_players(selection):
    white = PLAYER_BUILDERS[selection["W"]]("W")
    black = PLAYER_BUILDERS[selection["B"]]("B")
    return white, black


def run_game():
    board = create_board()
    gui = GUI()

    selection = gui.show_start_menu(OPTION_DEFS, default_white="minimax", default_black="mcts")
    white, black = build_players(selection)
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

    gui.add_log("Game started!")
    gui.add_log(f"White: {white.name}")
    gui.add_log(f"Black: {black.name}")
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

        if is_stalemate(board, current):
            gui.add_log("Stalemate - Draw!")
            gui.update(board, "Stalemate!", move_num, current_turn=current, last_move_time=last_move_time)
            pygame.time.delay(1000)
            gui.show_winner("Draw - Stalemate!", board)
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

        worker = AIWorker(player, board)
        think_start = time.time()
        worker.start()

        dot_chars = [".", "..", "...", "...."]
        dot_idx = 0
        while worker.is_alive():
            spinner = dot_chars[dot_idx % len(dot_chars)]
            gui.update(
                board,
                f"{color_name} thinking{spinner}",
                move_num,
                check_king=check_king_pos,
                current_turn=current,
                last_move_time=last_move_time,
            )
            pygame.time.delay(THINK_POLL_MS)
            dot_idx += 1

        last_move_time = time.time() - think_start
        result = worker.result

        if result is None:
            gui.add_log(f"{color_name} has no moves - Draw!")
            gui.show_winner("Draw - No Moves!", board)
            return

        piece, dest = result
        r0, c0 = piece.row, piece.col
        r1, c1 = dest

        notation = (
            f"{'W' if current == 'W' else 'B'}"
            f"{move_num // 2 + 1}: "
            f"{piece_name(piece)} "
            f"{col_letter(c0)}{6-r0}->{col_letter(c1)}{6-r1}"
        )
        if in_check:
            notation += " (escapes check)"

        apply_move(board, piece, dest)
        move_num += 1

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
            last_move=((r0, c0), (r1, c1)),
            check_king=opp_check_pos,
            current_turn=opponent,
            last_move_time=last_move_time,
            seconds=MOVE_DELAY_SEC,
        )

        current = opponent


if __name__ == "__main__":
    run_game()
