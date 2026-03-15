# ai_mcts.py — Player 2: Monte Carlo Tree Search (MCTS) — IMPROVED
#
# Improvements over v1:
#   1. Immediate win detection   — checks for checkmate-in-1 before any simulation
#   2. Smart expansion ordering  — tries captures > promotions > centre > rest first
#   3. Better rollout policy     — always escapes check, takes promotions, avoids draws when winning
#   4. Tree reuse                — reuses subtree from the previous move (saves work)
#   5. Continuous scoring        — backpropagates material score (not just +1/0/-1)
#   6. Draw avoidance            — penalises draws when MCTS is materially ahead

import math
import random
import copy
import time

from board import (get_legal_moves, apply_move, is_checkmate,
                   is_stalemate, is_in_check)
from pieces import King, Queen, Knight, Pawn

# ── Tuning constants ──────────────────────────────────────────────────────────
SIMULATIONS  = 1000
MAX_ROLLOUT  = 50
UCB_C        = 1.41
TIME_LIMIT   = 4.5
PIECE_VALS   = {Queen: 9, Knight: 3, Pawn: 1, King: 0}
CENTER       = {(2,2),(2,3),(3,2),(3,3)}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def material(board, color):
    return sum(PIECE_VALS.get(type(p), 0)
               for row in board for p in row
               if p and p.color == color)


def material_score(board, mcts_color):
    """Continuous result in [-1,+1] based on material difference."""
    opp   = 'B' if mcts_color == 'W' else 'W'
    my_m  = material(board, mcts_color)
    opp_m = material(board, opp)
    total = my_m + opp_m
    if total == 0:
        return 0.0
    return max(-1.0, min(1.0, (my_m - opp_m) / total))


def move_priority(piece, dest, board):
    """
    Score a move for ordering (higher = expand / try first).
    Captures > Promotions > Centre > Advance pawns > rest
    """
    score  = 0
    target = board[dest[0]][dest[1]]
    if target is not None:
        victim   = PIECE_VALS.get(type(target), 0)
        attacker = PIECE_VALS.get(type(piece), 0)
        score   += 10 + victim - attacker * 0.1   # MVV-LVA
    if isinstance(piece, Pawn):
        if (piece.color == 'W' and dest[0] == 0) or \
           (piece.color == 'B' and dest[0] == 5):
            score += 20                            # promotion
        elif piece.color == 'B':
            score += dest[0] * 0.3
        else:
            score += (5 - dest[0]) * 0.3
    if dest in CENTER:
        score += 2
    return score


# ─────────────────────────────────────────────────────────────────────────────
# IMPROVEMENT 1 — Immediate checkmate detection
# ─────────────────────────────────────────────────────────────────────────────

def find_immediate_checkmate(board, color):
    """Return a move causing immediate checkmate, or None."""
    opponent = 'B' if color == 'W' else 'W'
    for piece, dest in get_legal_moves(board, color):
        nb = apply_move(board, piece, dest)
        if is_checkmate(nb, opponent):
            return (piece, dest)
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Node
# ─────────────────────────────────────────────────────────────────────────────

class Node:
    __slots__ = ('board','color','parent','move','wins','visits','children','untried')

    def __init__(self, board, color, parent=None, move=None):
        self.board    = board
        self.color    = color
        self.parent   = parent
        self.move     = move
        self.wins     = 0.0
        self.visits   = 0
        self.children = []
        self.untried  = None

    # IMPROVEMENT 2 — smart ordering: sort ascending, pop from end = best first
    def _init_untried(self):
        moves = get_legal_moves(self.board, self.color)
        moves.sort(key=lambda m: move_priority(m[0], m[1], self.board))
        self.untried = moves

    def is_terminal(self):
        return (is_checkmate(self.board, self.color) or
                is_stalemate(self.board, self.color))

    def is_fully_expanded(self):
        if self.untried is None:
            self._init_untried()
        return len(self.untried) == 0

    def ucb1(self, parent_visits):
        if self.visits == 0:
            return float('inf')
        return (self.wins / self.visits +
                UCB_C * math.sqrt(math.log(parent_visits) / self.visits))

    def best_child_ucb(self):
        return max(self.children, key=lambda c: c.ucb1(self.visits))

    def best_child_visits(self):
        return max(self.children, key=lambda c: c.visits)

    def expand(self):
        if self.untried is None:
            self._init_untried()
        move        = self.untried.pop()   # highest priority
        piece, dest = move
        new_board   = apply_move(self.board, piece, dest)
        opponent    = 'B' if self.color == 'W' else 'W'
        child       = Node(new_board, opponent, parent=self, move=move)
        self.children.append(child)
        return child


# ─────────────────────────────────────────────────────────────────────────────
# IMPROVEMENT 3 — Better rollout policy
# ─────────────────────────────────────────────────────────────────────────────

def rollout(board, color, mcts_color):
    """
    Simulate a game with smart policy:
      - Always take an immediate checkmate
      - Always take a promotion
      - Weighted random otherwise (captures preferred)
      - IMPROVEMENT 5: return continuous material score at depth limit
      - IMPROVEMENT 6: penalise draws when materially ahead
    """
    current = color

    for _ in range(MAX_ROLLOUT):
        opponent_of_current = 'B' if current == 'W' else 'W'

        if is_checkmate(board, current):
            winner = opponent_of_current
            return 1.0 if winner == mcts_color else -1.0

        if is_stalemate(board, current):
            # IMPROVEMENT 6 — draw avoidance
            mat = material_score(board, mcts_color)
            return -0.3 if mat > 0.2 else 0.0

        moves = get_legal_moves(board, current)
        if not moves:
            mat = material_score(board, mcts_color)
            return -0.3 if mat > 0.2 else 0.0

        # Always take immediate checkmate
        for piece, dest in moves:
            nb = apply_move(board, piece, dest)
            if is_checkmate(nb, opponent_of_current):
                board   = nb
                winner  = current
                return 1.0 if winner == mcts_color else -1.0

        # Always take a promotion
        promo = [(p, d) for p, d in moves
                 if isinstance(p, Pawn) and
                    ((p.color=='W' and d[0]==0) or (p.color=='B' and d[0]==5))]
        if promo:
            piece, dest = promo[0]
            board   = apply_move(board, piece, dest)
            current = opponent_of_current
            continue

        # Weighted random — captures + centre preferred
        weighted = []
        for piece, dest in moves:
            w      = 1.0
            target = board[dest[0]][dest[1]]
            if target is not None:
                w += PIECE_VALS.get(type(target), 0) * 2.0
            if dest in CENTER:
                w += 1.5
            if isinstance(piece, Pawn):
                adv = dest[0] if current == 'B' else (5 - dest[0])
                w  += adv * 0.2
            weighted.append((w, piece, dest))

        total  = sum(w for w,_,_ in weighted)
        r      = random.uniform(0, total)
        cumul  = 0.0
        chosen = weighted[-1]
        for item in weighted:
            cumul += item[0]
            if cumul >= r:
                chosen = item
                break

        board   = apply_move(board, chosen[1], chosen[2])
        current = opponent_of_current

    # IMPROVEMENT 5 — continuous score instead of hard +1/-1 guess
    return material_score(board, mcts_color)


# ─────────────────────────────────────────────────────────────────────────────
# IMPROVEMENT 4 — Board equality check for tree reuse
# ─────────────────────────────────────────────────────────────────────────────

def _boards_equal(b1, b2):
    for r in range(6):
        for c in range(6):
            p1, p2 = b1[r][c], b2[r][c]
            if type(p1) != type(p2):
                return False
            if p1 is not None and p1.color != p2.color:
                return False
    return True


# ─────────────────────────────────────────────────────────────────────────────
# Main MCTS search
# ─────────────────────────────────────────────────────────────────────────────

def mcts_search(board, color, n_simulations=SIMULATIONS,
                time_limit=TIME_LIMIT, reuse_root=None):
    """
    Run MCTS and return (best_move, root_node).
    Pass reuse_root from the previous call for tree reuse.
    """
    # IMPROVEMENT 1 — free win check
    instant_win = find_immediate_checkmate(board, color)
    if instant_win:
        return instant_win, None

    # IMPROVEMENT 4 — try to reuse existing tree
    root = None
    if reuse_root is not None:
        for child in reuse_root.children:
            for grandchild in child.children:
                if _boards_equal(grandchild.board, board):
                    grandchild.parent = None
                    root = grandchild
                    break
            if root:
                break

    if root is None:
        root = Node(board, color)

    start     = time.time()
    sim_count = 0

    while sim_count < n_simulations and (time.time() - start) < time_limit:

        # 1. SELECT
        node = root
        while not node.is_terminal() and node.is_fully_expanded():
            node = node.best_child_ucb()

        # 2. EXPAND
        if not node.is_terminal() and not node.is_fully_expanded():
            node = node.expand()

        # 3. SIMULATE
        result = rollout(copy.deepcopy(node.board), node.color, color)

        # 4. BACKPROPAGATE — IMPROVEMENT 5: continuous score propagated correctly
        n = node
        while n is not None:
            n.visits += 1
            # Nodes where it was our turn to move → we benefit from +result
            # Nodes where it was opponent's turn  → they lose when result is high
            if n.color != color:
                n.wins += result
            else:
                n.wins -= result
            n = n.parent

        sim_count += 1

    if not root.children:
        legal = get_legal_moves(board, color)
        fallback = random.choice(legal) if legal else None
        return fallback, None

    best = root.best_child_visits()
    return best.move, root


# ─────────────────────────────────────────────────────────────────────────────
# MCTSPlayer
# ─────────────────────────────────────────────────────────────────────────────

class MCTSPlayer:
    def __init__(self, color='B', simulations=SIMULATIONS):
        self.color       = color
        self.simulations = simulations
        self.name        = f"MCTS+ ({simulations} sims)"
        self._root       = None   # stored tree root for reuse

    def choose_move(self, board):
        move, new_root = mcts_search(
            board, self.color,
            n_simulations = self.simulations,
            reuse_root    = self._root,
        )
        self._root = new_root   # save for next call (tree reuse)
        return move