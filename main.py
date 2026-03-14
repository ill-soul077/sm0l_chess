# main.py — SmoL Chess: Minimax (White) vs Fuzzy Logic (Black)
# AI runs in a background thread so the GUI never freezes.

import threading
import time
import pygame

from board import create_board, apply_move, is_checkmate, is_stalemate, is_in_check, find_king
from ai_minimax import MinimaxPlayer
from ai_fuzzy import FuzzyPlayer
from gui import GUI
from pieces import King, Queen, Knight, Pawn

MAX_MOVES       = 200   # draw after this many half-moves
MOVE_DELAY_SEC  = 5.0   # seconds to pause AFTER each move so visitors can watch
THINK_POLL_MS   = 50    # how often (ms) we pump pygame events while AI thinks


# ── Helpers ───────────────────────────────────────────────────────────────────

def piece_name(piece):
    names = {King: 'King', Queen: 'Queen', Knight: 'Knight', Pawn: 'Pawn'}
    return names.get(type(piece), '?')

def col_letter(c):
    return 'abcdef'[c]


# ── Threaded AI call ──────────────────────────────────────────────────────────

class AIWorker(threading.Thread):
    def __init__(self, player, board):
        super().__init__(daemon=True)
        self.player = player
        self.board  = board
        self.result = None

    def run(self):
        self.result = self.player.choose_move(self.board)


# ── Countdown helper ──────────────────────────────────────────────────────────

def wait_with_countdown(gui, board, status, move_num, last_move, check_king,
                        seconds=MOVE_DELAY_SEC):
    """
    Show a live countdown on the GUI while the game pauses between moves.
    Keeps pumping pygame events so the window stays responsive.
    """
    start = time.time()
    while True:
        elapsed   = time.time() - start
        remaining = seconds - elapsed
        if remaining <= 0:
            break
        countdown_status = f"{status}  [{remaining:.1f}s]"
        gui.update(board, countdown_status, move_num,
                   last_move=last_move, check_king=check_king)
        pygame.time.delay(80)


# ── Main game loop ────────────────────────────────────────────────────────────

def run_game():
    board   = create_board()
    gui     = GUI()

    white   = MinimaxPlayer(color='W', depth=3)
    black   = FuzzyPlayer(color='B')
    players = {'W': white, 'B': black}

    current  = 'W'
    move_num = 0

    gui.add_log("Game started!")
    gui.add_log(f"White: {white.name}")
    gui.add_log(f"Black: {black.name}")

    while True:
        player     = players[current]
        opponent   = 'B' if current == 'W' else 'W'
        color_name = "White" if current == 'W' else "Black"

        # ── Terminal checks ───────────────────────────────────────────────────
        if is_checkmate(board, current):
            winner = "White" if current == 'B' else "Black"
            msg    = f"{winner} wins by Checkmate!"
            gui.add_log(f"CHECKMATE! {msg}")
            gui.update(board, "Checkmate!", move_num)
            pygame.time.delay(1000)
            gui.show_winner(msg, board)
            return

        if is_stalemate(board, current):
            gui.add_log("Stalemate — Draw!")
            gui.update(board, "Stalemate!", move_num)
            pygame.time.delay(1000)
            gui.show_winner("Draw — Stalemate!", board)
            return

        if move_num >= MAX_MOVES:
            gui.add_log("Move limit — Draw!")
            gui.update(board, "Draw!", move_num)
            pygame.time.delay(1000)
            gui.show_winner("Draw — Move Limit!", board)
            return

        # ── Show "thinking" while AI works in background ──────────────────────
        in_check       = is_in_check(board, current)
        check_king_pos = None
        if in_check:
            k = find_king(board, current)
            if k:
                check_king_pos = (k.row, k.col)

        # Launch AI in a background thread
        worker = AIWorker(player, board)
        worker.start()

        # Animate spinner while waiting — GUI stays alive
        dot_chars = ['⠋','⠙','⠹','⠸','⠼','⠴','⠦','⠧','⠇','⠏']
        dot_idx   = 0
        while worker.is_alive():
            spinner = dot_chars[dot_idx % len(dot_chars)]
            gui.update(board, f"{spinner} {color_name} thinking...",
                       move_num, check_king=check_king_pos)
            pygame.time.delay(THINK_POLL_MS)
            dot_idx += 1

        result = worker.result

        if result is None:
            gui.add_log(f"{color_name} has no moves — Draw!")
            gui.show_winner("Draw — No Moves!", board)
            return

        piece, dest = result
        r0, c0      = piece.row, piece.col
        r1, c1      = dest

        notation = (f"{'W' if current=='W' else 'B'}"
                    f"{move_num//2+1}: "
                    f"{piece_name(piece)} "
                    f"{col_letter(c0)}{6-r0}→{col_letter(c1)}{6-r1}")
        if in_check:
            notation += " (escapes check)"

        board    = apply_move(board, piece, dest)
        move_num += 1

        opp_in_check = is_in_check(board, opponent)
        if opp_in_check:
            notation += " +"
        gui.add_log(notation)

        opp_check_pos = None
        if opp_in_check:
            k = find_king(board, opponent)
            if k:
                opp_check_pos = (k.row, k.col)

        move_status = f"{'⚠ Check!' if opp_in_check else color_name + ' moved'}"

        # ── 5-second countdown so visitors can study the position ─────────────
        wait_with_countdown(
            gui, board,
            status     = move_status,
            move_num   = move_num,
            last_move  = ((r0, c0), (r1, c1)),
            check_king = opp_check_pos,
            seconds    = MOVE_DELAY_SEC,
        )

        current = opponent


if __name__ == "__main__":
    run_game()