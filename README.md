# SmoL Chess AI Project

SmoL Chess is a custom 6x6 chess-variant project written in Python. It includes a complete board engine, a Pygame graphical interface, human play, and three different AI approaches: Minimax, Monte Carlo Tree Search, and Fuzzy Logic.

The project is designed as both a playable mini-chess demo and an academic comparison of different AI decision-making methods on the same simplified rule set.

## Features

- Custom 6x6 chess-like board
- Four piece types: King, Queen, Knight, and Pawn
- Legal move generation with self-check prevention
- Check, checkmate, stalemate, threefold repetition, 50-move rule, insufficient-material draw, and move-limit draw
- Pawn first-move double advance
- Automatic pawn promotion to Queen
- Human vs AI, Human vs Human, and AI vs AI matchups
- Start menu for choosing White and Black players
- AI max-think-time slider
- Pygame GUI with board coordinates, sprites, highlights, move log, and winner overlay
- Scrollable newest-first move log
- Stale AI move protection when a timed-out AI returns an outdated move
- Three AI players:
  - Minimax with alpha-beta pruning
  - Monte Carlo Tree Search
  - Fuzzy Logic rule-based player

## How To Run

The project uses Python and Pygame. On the current Python 3.14 setup, `pygame-ce` is recommended because the regular `pygame` wheel can have font issues.

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the dependency:

```bash
pip install pygame-ce
```

Run the game:

```bash
python main.py
```

If you are not activating the virtual environment, run:

```bash
.venv/bin/python main.py
```

## Project Structure

```text
sm0l_chess/
├── main.py                  Main game loop, player selection, AI threading
├── gui.py                   Pygame GUI, menu, board rendering, side panel, logs
├── board.py                 Board state, legal moves, check/checkmate/stalemate
├── pieces.py                Piece classes and movement rules
├── game_rules.py            Match-level draw rules and repetition tracking
├── ai_minimax.py            Minimax AI with alpha-beta pruning
├── ai_mcts.py               Monte Carlo Tree Search AI
├── ai_fuzzy.py              Fuzzy Logic AI
├── assets/
│   ├── pieces/              Piece PNG sprites
│   └── ui/                  UI texture assets
└── 2107065_2107077.pdf      Project report
```

## Running A Match

When the program starts, the menu lets you choose both players:

- `Human`
- `Minimax`
- `MCTS`
- `Fuzzy Logic`

The current default setup is:

- White: Human
- Black: MCTS

The menu also includes an AI max-think-time slider. This limits the amount of time search-based AI players are allowed to spend on a move. MCTS and Minimax both cooperate with the time limit. If an AI still returns late or returns a stale move from an old board copy, the main loop validates the move against the current legal moves and uses a legal fallback instead of crashing.

## Human Controls

For a human turn:

1. Click one of your pieces.
2. Legal target squares are highlighted.
3. Click a highlighted square to move.

Other controls:

- Close the window to quit.
- Use the mouse wheel over the move-log panel to scroll through older logs.
- The newest log entries appear at the top.

## Game Rules

SmoL Chess is not standard chess. It is a small custom variant built for easier AI experimentation.

### Board

- The board is 6x6.
- Rows are indexed internally from `0` to `5`.
- Columns are indexed internally from `0` to `5`.
- The GUI labels files as `a` to `f`.
- The GUI labels ranks as `1` to `6`.

### Pieces

Each side starts with:

- 1 King
- 1 Queen
- 2 Knights
- 2 Pawns

There are no:

- Rooks
- Bishops
- Castling
- En passant

### Initial Position

Black starts on row `0`:

```text
Pawn  Knight  Queen  King  Knight  Pawn
```

White starts on row `5`:

```text
Pawn  Knight  Queen  King  Knight  Pawn
```

Rows `1` through `4` are empty at the start.

### King

The King moves one square in any direction and captures normally.

### Queen

The Queen is range-limited:

- It moves horizontally, vertically, or diagonally.
- It can move at most 2 squares.
- It cannot jump over pieces.

This makes the Queen weaker than a standard chess Queen and keeps the small board from becoming too tactical too quickly.

### Knight

The Knight moves like a normal chess Knight:

- Two squares in one direction and one square perpendicular.
- It can jump over other pieces.

### Pawn

White pawns move toward row `0`. Black pawns move toward row `5`.

Pawns can:

- Move 1 square forward if empty.
- Move 2 squares forward on their first move if both squares are clear.
- Capture diagonally forward.
- Promote automatically to a Queen on the final row.

### Legal Moves

A move is legal only if it does not leave the moving side's King in check.

The board engine generates pseudo-legal moves from the pieces, applies them temporarily, checks whether the King remains safe, and only keeps legal moves.

### Check

A King is in check if any opponent piece attacks the King's square.

### Checkmate

A side is checkmated when:

- Its King is in check.
- It has no legal move that removes the check.

### Stalemate

A side is stalemated when:

- Its King is not in check.
- It has no legal move.

### Draw Rules

The project includes several draw rules inspired by common chess rules:

- Stalemate
- Threefold repetition
- 50-move rule
- Insufficient material
- Fixed move limit

The fixed move limit is controlled by `MAX_MOVES = 200` in `main.py`.

Threefold repetition and the 50-move rule are tracked in `game_rules.py`. The position key includes:

- Side to move
- Piece type
- Piece color
- Piece square
- Pawn first-move state

Pawn first-move state matters because it changes whether a 2-square pawn move is legal.

## AI Players

All AI players expose a `choose_move(board, draw_context=None)` method. The main loop runs AI calculations in a background thread so the GUI can keep updating.

The main loop always validates the returned move against the current live board before applying it. This is important because AI players search on copied boards, and a timed-out thread can otherwise return a move that no longer matches the current board.

### Minimax AI

File: `ai_minimax.py`

The Minimax player uses depth-limited adversarial search with alpha-beta pruning.

Main ideas:

- Search alternates between maximizing the AI score and minimizing the opponent score.
- Alpha-beta pruning skips branches that cannot affect the final decision.
- Iterative deepening is used so a valid move is available if the time limit is reached.
- A transposition table stores searched board states during a search.
- Draw positions evaluate as `0`.
- Checkmate dominates all heuristic scores.

Evaluation considers:

- Material balance
- Legal move mobility
- Center control
- King safety

The AI prefers:

```text
win > advantage > draw > disadvantage > loss
```

This means it avoids draws when winning, but it prefers a draw over losing.

### MCTS AI

File: `ai_mcts.py`

The MCTS player uses Monte Carlo Tree Search.

Main ideas:

- Build a search tree of possible moves.
- Select promising nodes using UCB1.
- Expand unexplored moves.
- Simulate rollouts from those positions.
- Backpropagate results through the tree.

The implementation includes:

- UCB1 node selection
- Move ordering for expansion
- Tactical rollout scoring
- Immediate checkmate detection
- Time-limited search
- Draw-aware rollouts
- Tree reuse when possible

Rollouts return:

- `1.0` for a win
- `0.0` for a draw
- `-1.0` for a loss
- Material-based scores for unfinished rollouts

MCTS also treats draws as better than losses but worse than wins.

### Fuzzy Logic AI

File: `ai_fuzzy.py`

The Fuzzy Logic player scores each legal move using rule-based fuzzy-inspired heuristics.

It evaluates:

- Material advantage
- King danger
- Center control
- Captures
- Checks
- Checkmates
- Promotions
- Whether the moved piece becomes hanging
- Whether a move immediately causes a draw

The fuzzy player is much faster than search-based players. It does not search deeply, so it is less tactically precise, but it is useful for comparing rule-based decision-making against Minimax and MCTS.

## GUI

File: `gui.py`

The GUI is built with Pygame.

It includes:

- Start menu with player selection
- AI max-think-time slider
- 6x6 board rendering
- Piece sprites from `assets/pieces/`
- Board coordinates
- Last move highlighting
- Check highlighting
- Human legal-move highlights
- Right-side wooden information panel
- Player cards
- Current status card
- Scrollable move log
- Winner overlay
- Basic move animation

The window uses the native operating-system title bar. Earlier custom title-bar experiments were removed because moving a borderless Pygame window was unreliable on this environment.

## Important Implementation Details

### Board Representation

The board is a 6x6 list of lists:

```python
board[row][col]
```

Each square contains either:

- `None`
- a `Piece` object

Piece objects store:

- `color`
- `row`
- `col`
- `symbol`

Pawns also store:

- `has_moved`

### Applying And Undoing Moves

`board.py` provides:

- `apply_move(board, piece, dest)`
- `undo_move(board, undo_token)`

`apply_move` mutates the board and returns an undo token. This lets legal-move generation and AI search test moves efficiently without rebuilding every detail manually.

### Copying Boards

AI search uses copied boards so it can explore future positions without changing the live game. The function `copy_board(board)` creates independent piece objects, including pawn `has_moved` state.

### Stale Move Protection

AI threads search on board copies. When an AI time limit is very short, the main loop may use a fallback move while the AI thread finishes later. To avoid stale moves causing crashes, `main.py` resolves every AI move back to the current board using:

```python
resolve_current_legal_move(board, color, move)
```

If the move no longer exists as a current legal move, the game logs the issue and chooses a legal fallback.

## Assets

Piece sprites are stored in:

```text
assets/pieces/
```

Expected files:

```text
wk.png  wq.png  wn.png  wp.png
bk.png  bq.png  bn.png  bp.png
```

UI texture assets are stored in:

```text
assets/ui/
```

## Configuration

Main constants:

- `MAX_MOVES = 200` in `main.py`
- `MOVE_DELAY_SEC = 0.25` in `main.py`
- Default Minimax depth: `3`
- Default MCTS simulations from `main.py`: `800`
- MCTS module default simulations: `1000`
- MCTS module default time limit: `4.5`
- GUI AI time slider range: `0.5s` to `10.0s`

Draw constants in `game_rules.py`:

- `THREEFOLD_REPETITION_COUNT = 3`
- `FIFTY_MOVE_HALFMOVES = 100`

## Current Limitations

- No automated test suite is included.
- No tournament or batch evaluation mode is included.
- No save/load feature is included.
- AI strength is tuned for demonstration, not competitive play.
- MCTS and Minimax still rely heavily on board copying.
- The Fuzzy AI is fast but shallow.
- The GUI is fixed-size.

## Suggested Future Improvements

- Add unit tests for movement, check, checkmate, stalemate, draw rules, and promotion.
- Add command-line options for player types and AI settings.
- Add match export to CSV or JSON for AI comparison.
- Add tournament mode for repeated AI-vs-AI evaluation.
- Add pause, restart, and rematch controls.
- Add profiling and optimize board copying in search.
- Tune AI evaluation weights using match results.

## Summary

SmoL Chess is a complete mini-chess AI playground. It includes a custom rule set, working board engine, human play, three AI strategies, draw-rule tracking, a graphical interface, and configurable AI thinking time.

The main educational value of the project is that Minimax, MCTS, and Fuzzy Logic all operate on the same game rules, making their behavior easier to compare and explain.
