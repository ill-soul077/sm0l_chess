# main.py — SmoL Chess: Minimax (White) vs Fuzzy Logic (Black)
# AI runs in a background thread so the GUI never freezes.

import threading
import time
import pygame

from board import create_board, apply_move, is_checkmate, is_stalemate, is_in_check, find_king, get_legal_moves
from ai_minimax import MinimaxPlayer, evaluate
from ai_mcts import MCTSPlayer
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


def position_key(board, side_to_move):
    """
    Hashable board state key for repetition detection.
    Includes side to move and pawn has_moved flags because they affect legal moves.
    """
    rows = []
    for row in board:
        row_key = []
        for piece in row:
            if piece is None:
                row_key.append(None)
                continue
            p_type = type(piece).__name__
            pawn_moved = piece.has_moved if isinstance(piece, Pawn) else None
            row_key.append((piece.color, p_type, pawn_moved))
        rows.append(tuple(row_key))
    return (side_to_move, tuple(rows))


def would_trigger_threefold(board, move, mover_color, repetition_count):
    """Return True if applying move creates a position seen 3 times."""
    opponent = 'B' if mover_color == 'W' else 'W'
    next_board = apply_move(board, move[0], move[1])
    next_key = position_key(next_board, opponent)
    return repetition_count.get(next_key, 0) + 1 >= 3


def choose_non_repetition_move(board, mover_color, repetition_count):
    """
    Pick a legal move that avoids immediate threefold repetition, if one exists.
    Uses evaluation as a tie-breaker so the engine still pushes for wins.
    """
    opponent = 'B' if mover_color == 'W' else 'W'
    legal = get_legal_moves(board, mover_color)
    candidates = []

    for piece, dest in legal:
        next_board = apply_move(board, piece, dest)
        next_key = position_key(next_board, opponent)
        if repetition_count.get(next_key, 0) + 1 >= 3:
            continue
        candidates.append((piece, dest, next_board))

    if not candidates:
        return None

    def score(candidate):
        piece, dest, next_board = candidate
        if is_checkmate(next_board, opponent):
            return 1_000_000

        val = evaluate(next_board, mover_color)

        # Prefer avoiding stalemate unless already in a clearly losing state.
        if is_stalemate(next_board, opponent) and val > -1.5:
            val -= 5.0

        if is_in_check(next_board, opponent):
            val += 0.35

        return val

    best = max(candidates, key=score)
    return (best[0], best[1])


# ── Threaded AI call ──────────────────────────────────────────────────────────

class AIWorker(threading.Thread):
    def __init__(self, player, board):
        super().__init__(daemon=True)
        self.player = player
        self.board  = board
        self.result = None
        self.error  = None

    def run(self):
        try:
            self.result = self.player.choose_move(self.board)
        except Exception as exc:
            self.error = exc
            self.result = None


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
    #black   = MCTSPlayer(color='B', simulations=800)
    black   = MinimaxPlayer(color='B', depth=3)
    players = {'W': white, 'B': black}

    current  = 'W'
    move_num = 0

    # Threefold repetition tracking: same position + same side to move.
    repetition_count = {}
    start_key = position_key(board, current)
    repetition_count[start_key] = 1

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

        if worker.error is not None:
            # Keep the game alive if an AI thread crashes on one position.
            gui.add_log(f"{color_name} AI error, using fallback move")
            legal_fallback = get_legal_moves(board, current)
            if legal_fallback:
                def fb_score(move):
                    nb = apply_move(board, move[0], move[1])
                    return evaluate(nb, current)
                result = max(legal_fallback, key=fb_score)

        if result is None:
            # Safety net: if legal moves exist but AI returned None, do not force a false draw.
            legal_fallback = get_legal_moves(board, current)
            if legal_fallback:
                gui.add_log(f"{color_name} returned no move, using fallback legal move")
                def fb_score(move):
                    nb = apply_move(board, move[0], move[1])
                    return evaluate(nb, current)
                result = max(legal_fallback, key=fb_score)
            else:
                gui.add_log(f"{color_name} has no moves — Draw!")
                gui.show_winner("Draw — No Moves!", board)
                return

        piece, dest = result

        # Anti-draw policy: if chosen move causes 3-fold repetition, try another.
        if would_trigger_threefold(board, (piece, dest), current, repetition_count):
            alternative = choose_non_repetition_move(board, current, repetition_count)
            if alternative is not None:
                piece, dest = alternative

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

        # Next turn belongs to opponent after current side moves.
        next_position_key = position_key(board, opponent)
        repetition_count[next_position_key] = repetition_count.get(next_position_key, 0) + 1

        opp_in_check = is_in_check(board, opponent)
        if opp_in_check:
            notation += " +"
        gui.add_log(notation)

        if repetition_count[next_position_key] >= 3:
            gui.add_log("Threefold repetition — Draw!")
            gui.update(board, "Draw! (Repetition)", move_num,
                       last_move=((r0, c0), (r1, c1)))
            pygame.time.delay(1000)
            gui.show_winner("Draw — Threefold Repetition!", board)
            return

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