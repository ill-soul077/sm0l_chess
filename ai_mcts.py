# ai_mcts.py - Monte Carlo Tree Search with move ordering, tree reuse,
# and a rollout policy that prefers tactical, non-blundering moves.

import math
import random
import time

from board import (
    apply_move,
    copy_board,
    get_legal_moves,
    is_checkmate,
    is_in_check,
    is_stalemate,
    undo_move,
)
from pieces import King, Knight, Pawn, Queen

SIMULATIONS = 1000
MAX_ROLLOUT = 50
UCB_C = 1.41
TIME_LIMIT = 4.5
ROLLOUT_TEMPERATURE = 15.0
PIECE_VALS = {Queen: 9, Knight: 3, Pawn: 1, King: 0}
CENTER = {(2, 2), (2, 3), (3, 2), (3, 3)}


def material(board, color):
    return sum(
        PIECE_VALS.get(type(piece), 0)
        for row in board
        for piece in row
        if piece and piece.color == color
    )


def material_score(board, mcts_color):
    """Continuous result in [-1,+1] based on material difference."""
    opponent = "B" if mcts_color == "W" else "W"
    my_material = material(board, mcts_color)
    opp_material = material(board, opponent)
    total = my_material + opp_material
    if total == 0:
        return 0.0
    return max(-1.0, min(1.0, (my_material - opp_material) / total))


def move_key(piece, dest):
    return ((piece.row, piece.col), dest)


def translate_move(board, color, move):
    if move is None:
        return None
    target_key = move_key(*move)
    for legal_piece, legal_dest in get_legal_moves(board, color):
        if move_key(legal_piece, legal_dest) == target_key:
            return (legal_piece, legal_dest)
    return None


def is_square_attacked(board, square, by_color):
    target_row, target_col = square
    for row in board:
        for piece in row:
            if piece and piece.color == by_color:
                if (target_row, target_col) in piece.get_moves(board):
                    return True
    return False


def count_attackers(board, square, by_color):
    target_row, target_col = square
    count = 0
    for row in board:
        for piece in row:
            if piece and piece.color == by_color:
                if (target_row, target_col) in piece.get_moves(board):
                    count += 1
    return count


def move_priority(piece, dest, board):
    """
    Score a move for tree expansion ordering.
    Captures > Promotions > Centre > Advance pawns > rest.
    """
    score = 0.0
    target = board[dest[0]][dest[1]]
    if target is not None:
        victim = PIECE_VALS.get(type(target), 0)
        attacker = PIECE_VALS.get(type(piece), 0)
        score += 10.0 + victim - attacker * 0.1
    if isinstance(piece, Pawn):
        if (piece.color == "W" and dest[0] == 0) or (piece.color == "B" and dest[0] == 5):
            score += 20.0
        elif piece.color == "B":
            score += dest[0] * 0.3
        else:
            score += (5 - dest[0]) * 0.3
    if dest in CENTER:
        score += 2.0
    return score


def find_immediate_checkmate(board, color):
    """Return a move causing immediate checkmate, or None."""
    opponent = "B" if color == "W" else "W"
    for piece, dest in get_legal_moves(board, color):
        undo = apply_move(board, piece, dest)
        is_mate = is_checkmate(board, opponent)
        undo_move(board, undo)
        if is_mate:
            return (piece, dest)
    return None


def rollout_move_score(board, piece, dest, color):
    opponent = "B" if color == "W" else "W"
    before_material = material(board, color) - material(board, opponent)
    captured = board[dest[0]][dest[1]]
    undo = apply_move(board, piece, dest)
    moved_piece = board[dest[0]][dest[1]]
    score = 0.0

    if is_checkmate(board, opponent):
        undo_move(board, undo)
        return 100000.0

    if isinstance(piece, Pawn) and ((piece.color == "W" and dest[0] == 0) or (piece.color == "B" and dest[0] == 5)):
        score += 350.0

    if captured is not None:
        score += 100.0 + PIECE_VALS.get(type(captured), 0) * 35.0

    if is_in_check(board, opponent):
        score += 80.0

    if dest in CENTER:
        score += 18.0

    if isinstance(piece, Pawn):
        score += dest[0] * 4.0 if color == "B" else (5 - dest[0]) * 4.0

    attackers = count_attackers(board, dest, opponent)
    defenders = count_attackers(board, dest, color)
    if attackers > 0:
        hanging_penalty = 90.0 + PIECE_VALS.get(type(moved_piece), 0) * 20.0
        score -= hanging_penalty
        if defenders == 0:
            score -= 60.0
        elif defenders < attackers:
            score -= 25.0

    if is_in_check(board, color):
        score -= 250.0

    opponent_wins = 0
    for opp_piece, opp_dest in get_legal_moves(board, opponent):
        reply_target = board[opp_dest[0]][opp_dest[1]]
        reply_undo = apply_move(board, opp_piece, opp_dest)
        if is_checkmate(board, color):
            opponent_wins += 1
        if reply_target is not None and PIECE_VALS.get(type(reply_target), 0) >= 3:
            score -= 40.0
        undo_move(board, reply_undo)
    if opponent_wins:
        score -= 500.0

    after_material = material(board, color) - material(board, opponent)
    score += (after_material - before_material) * 12.0
    undo_move(board, undo)
    return score


def select_rollout_move(board, moves, color):
    scored = []
    for piece, dest in moves:
        scored.append((rollout_move_score(board, piece, dest, color), piece, dest))

    scored.sort(key=lambda item: item[0], reverse=True)
    top = scored[:3]
    max_score = max(item[0] for item in top)

    weights = []
    for score, _, _ in top:
        weights.append(math.exp((score - max_score) / ROLLOUT_TEMPERATURE))

    chosen = random.choices(top, weights=weights, k=1)[0]
    return chosen[1], chosen[2]


class Node:
    __slots__ = ("board", "color", "parent", "move", "wins", "visits", "children", "untried")

    def __init__(self, board, color, parent=None, move=None):
        self.board = board
        self.color = color
        self.parent = parent
        self.move = move
        self.wins = 0.0
        self.visits = 0
        self.children = []
        self.untried = None

    def _init_untried(self):
        moves = get_legal_moves(self.board, self.color)
        moves.sort(key=lambda move: move_priority(move[0], move[1], self.board))
        self.untried = moves

    def is_terminal(self):
        return is_checkmate(self.board, self.color) or is_stalemate(self.board, self.color)

    def is_fully_expanded(self):
        if self.untried is None:
            self._init_untried()
        return len(self.untried) == 0

    def ucb1(self, parent_visits):
        if self.visits == 0:
            return float("inf")
        return (self.wins / self.visits) + UCB_C * math.sqrt(math.log(parent_visits) / self.visits)

    def best_child_ucb(self):
        return max(self.children, key=lambda child: child.ucb1(self.visits))

    def best_child_visits(self):
        return max(self.children, key=lambda child: child.visits)

    def expand(self):
        if self.untried is None:
            self._init_untried()
        move = self.untried.pop()
        piece, dest = move
        new_board = copy_board(self.board)
        apply_move(new_board, piece, dest)
        opponent = "B" if self.color == "W" else "W"
        child = Node(new_board, opponent, parent=self, move=move)
        self.children.append(child)
        return child


def rollout(board, color, mcts_color):
    current = color

    for _ in range(MAX_ROLLOUT):
        opponent = "B" if current == "W" else "W"

        if is_checkmate(board, current):
            winner = opponent
            return 1.0 if winner == mcts_color else -1.0

        if is_stalemate(board, current):
            score = material_score(board, mcts_color)
            return -0.3 if score > 0.2 else 0.0

        moves = get_legal_moves(board, current)
        if not moves:
            score = material_score(board, mcts_color)
            return -0.3 if score > 0.2 else 0.0

        forced_mate = find_immediate_checkmate(board, current)
        if forced_mate is not None:
            piece, dest = forced_mate
        else:
            piece, dest = select_rollout_move(board, moves, current)

        apply_move(board, piece, dest)
        current = opponent

    return material_score(board, mcts_color)


def _boards_equal(board_a, board_b):
    for row in range(6):
        for col in range(6):
            piece_a = board_a[row][col]
            piece_b = board_b[row][col]
            if type(piece_a) != type(piece_b):
                return False
            if piece_a is not None:
                if piece_a.color != piece_b.color:
                    return False
                if getattr(piece_a, "has_moved", False) != getattr(piece_b, "has_moved", False):
                    return False
    return True


def mcts_search(board, color, n_simulations=SIMULATIONS, time_limit=TIME_LIMIT, reuse_root=None):
    """
    Run MCTS and return (best_move, root_node).
    Pass reuse_root from the previous call for tree reuse.
    """
    root_board = copy_board(board)
    instant_win = find_immediate_checkmate(root_board, color)
    if instant_win:
        return translate_move(board, color, instant_win), None

    root = None
    if reuse_root is not None:
        for child in reuse_root.children:
            for grandchild in child.children:
                if _boards_equal(grandchild.board, root_board):
                    grandchild.parent = None
                    root = grandchild
                    break
            if root is not None:
                break

    if root is None:
        root = Node(root_board, color)

    start = time.time()
    simulations = 0

    while simulations < n_simulations and (time.time() - start) < time_limit:
        node = root

        while not node.is_terminal() and node.is_fully_expanded():
            node = node.best_child_ucb()

        if not node.is_terminal() and not node.is_fully_expanded():
            node = node.expand()

        result = rollout(copy_board(node.board), node.color, color)

        current = node
        while current is not None:
            current.visits += 1
            if current.color != color:
                current.wins += result
            else:
                current.wins -= result
            current = current.parent

        simulations += 1

    if not root.children:
        legal = get_legal_moves(root_board, color)
        fallback = random.choice(legal) if legal else None
        return translate_move(board, color, fallback), None

    best = root.best_child_visits()
    return translate_move(board, color, best.move), root


class MCTSPlayer:
    def __init__(self, color="B", simulations=SIMULATIONS):
        self.color = color
        self.simulations = simulations
        self.name = f"MCTS+ ({simulations} sims)"
        self._root = None

    def choose_move(self, board):
        move, new_root = mcts_search(
            board,
            self.color,
            n_simulations=self.simulations,
            reuse_root=self._root,
        )
        self._root = new_root
        return move
