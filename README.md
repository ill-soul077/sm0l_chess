# SmoL Chess AI Project

SmoL Chess is a custom 6x6 mini-chess project built in Python with a Pygame interface. The project focuses on implementing a small chess variant and comparing different AI decision-making approaches on the same ruleset.

The repository currently contains:

- A complete 6x6 board representation
- Piece movement logic for King, Queen, Knight, and Pawn
- Legal move generation with self-check prevention
- Check, checkmate, and stalemate detection
- Pawn promotion
- Three AI approaches:
  - Minimax with alpha-beta pruning
  - Monte Carlo Tree Search (MCTS)
  - Fuzzy Logic move selection
- A graphical Pygame interface for watching AI vs AI matches

## Project Goal

The main goal of the project is to build a simplified chess environment and test different artificial intelligence methods on the same game:

- Search-based AI using Minimax
- Simulation-based AI using MCTS
- Rule-based AI using Fuzzy Logic

This makes the project useful both as:

- a game AI implementation project
- an academic comparison project
- a visual demo of different AI strategies

## What Has Been Done So Far

The current codebase already implements the following major work:

1. Designed a custom 6x6 chess variant instead of standard 8x8 chess.
2. Created the internal board as a 6x6 matrix containing piece objects or empty squares.
3. Implemented piece classes in `pieces.py`.
4. Added movement logic for:
   - King
   - Queen
   - Knight
   - Pawn
5. Implemented pawn first-move logic with optional 2-square advance.
6. Implemented diagonal pawn captures.
7. Implemented automatic pawn promotion to Queen.
8. Added board copy-based move application logic in `board.py`.
9. Added legal move filtering so a move is only allowed if it does not leave the moving side in check.
10. Added king detection and check detection.
11. Added checkmate detection.
12. Added stalemate detection.
13. Built a Minimax AI with:
    - depth-limited search
    - alpha-beta pruning
    - evaluation based on material, mobility, center control, and king safety
14. Built an MCTS AI with:
    - simulation rollouts
    - move ordering
    - immediate checkmate detection
    - tree reuse
    - continuous scoring during backpropagation
15. Built a Fuzzy Logic AI with:
    - fuzzy material evaluation
    - fuzzy king danger evaluation
    - fuzzy center control evaluation
    - rule-based candidate move scoring
16. Built a Pygame GUI with:
    - chessboard rendering
    - coordinate labels
    - move log panel
    - winner overlay
    - last move highlight
    - check highlight
    - piece sprite loading
    - Unicode fallback if sprites are missing
    - lightweight piece animation
17. Added threaded AI move calculation so the GUI remains responsive while an AI is thinking.
18. Added a live thinking indicator and a short countdown after each move for spectators.
19. Added piece image assets in `assets/pieces/`.
20. Added a project report PDF in the repository.

## Current Run Configuration

The repository contains three AI agents, but the current default game setup in `main.py` is:

- White: `MinimaxPlayer(color='W', depth=3)`
- Black: `MinimaxPlayer(color='B', depth=3)`

Important note:

- `ai_mcts.py` is implemented and imported, but the active MCTS line in `main.py` is commented out.
- `ai_fuzzy.py` is implemented, but the Fuzzy player is not currently connected to the default game loop.

So at the moment, the project code supports three AI approaches, but the default executable match is currently Minimax vs Minimax.

## Project Structure

- `main.py`
  - Starts the game
  - Creates the board
  - Chooses the players
  - Runs the turn-by-turn game loop
  - Handles AI threads and match flow
- `board.py`
  - Creates the initial board
  - Applies moves on a copied board
  - Finds kings
  - Detects check, checkmate, and stalemate
  - Produces legal moves
- `pieces.py`
  - Defines the base `Piece` class
  - Defines `King`, `Queen`, `Knight`, and `Pawn`
  - Implements the move rules for each piece
- `ai_minimax.py`
  - Implements evaluation scoring
  - Implements Minimax search with alpha-beta pruning
- `ai_mcts.py`
  - Implements MCTS node expansion
  - Implements rollout policy
  - Implements search and tree reuse
- `ai_fuzzy.py`
  - Implements fuzzy heuristics
  - Scores candidate moves using rule-based logic
- `gui.py`
  - Draws the board and side panel
  - Loads and renders sprites
  - Draws highlights and animations
  - Shows match results
- `assets/pieces/`
  - Contains PNG piece images for both white and black pieces
- `2107065_2107077.pdf`
  - Project report file included in the repository

## Game Rules

This project does not use full standard chess. It uses a simplified custom variant.

### Board Size

- The board is `6 x 6`.
- Rows are indexed from `0` to `5`.
- Columns are indexed from `0` to `5`.
- The GUI labels columns as `a` to `f`.

### Pieces Used

Each side has 6 pieces:

- 1 King
- 1 Queen
- 2 Knights
- 2 Pawns

There are no:

- Rooks
- Bishops
- Castling
- En passant

### Initial Board Setup

All pieces start in a single back row for each side.

Black starts on row `0`:

```text
Pawn  Knight  Queen  King  Knight  Pawn
```

White starts on row `5`:

```text
Pawn  Knight  Queen  King  Knight  Pawn
```

Rows `1` to `4` are empty at the beginning.

### Piece Movement Rules

#### King

- Moves one square in any direction.
- Can capture opponent pieces normally.

#### Queen

- This is a range-limited queen, not a full standard chess queen.
- It can move in any of the 8 directions:
  - horizontal
  - vertical
  - diagonal
- It can move up to 2 squares only.
- It cannot jump over pieces.

#### Knight

- Moves in the usual L-shape:
  - 2 squares in one direction and 1 square perpendicular
- It can jump over other pieces.

#### Pawn

- White pawns move upward toward row `0`.
- Black pawns move downward toward row `5`.
- A pawn can move:
  - 1 square forward normally
  - 2 squares forward on its first move if the path is clear
- A pawn captures diagonally forward.
- When a pawn reaches the last row, it is promoted automatically to a Queen.

### Legal Move Rule

- A move is only legal if it does not leave the moving side's king in check.
- The game computes legal moves by generating candidate moves and filtering out moves that expose the king.

### Check

- A king is in check if an opponent piece can attack its square.

### Checkmate

- A side is in checkmate if:
  - its king is in check
  - it has no legal move to escape

### Stalemate

- A side is in stalemate if:
  - its king is not in check
  - it has no legal move

### Draw by Move Limit

- The game also declares a draw after a fixed move limit in `main.py`.
- The current value is `MAX_MOVES = 200` half-moves.

## AI Implementations

### 1. Minimax AI

The Minimax player is implemented in `ai_minimax.py`.

Current characteristics:

- Uses depth-limited recursive search
- Uses alpha-beta pruning to reduce unnecessary search
- Evaluates positions using:
  - material balance
  - mobility
  - center occupancy
  - king safety

Strengths:

- Deterministic and easy to explain
- Good for tactical search in smaller game trees
- Good baseline AI for comparison

Limitations:

- Gets slower as depth increases
- Recomputes many board states repeatedly
- Uses a relatively simple evaluation function

### 2. MCTS AI

The MCTS player is implemented in `ai_mcts.py`.

Current characteristics:

- Uses repeated simulations from candidate positions
- Uses UCB1 for node selection
- Uses move ordering to prefer promising expansions
- Includes immediate checkmate detection
- Includes tree reuse between turns
- Uses rollout scoring based on material balance when needed

Strengths:

- Flexible and useful for uncertain positions
- Can improve with more simulations
- Good research-oriented comparison against Minimax

Limitations:

- Slower than the current Fuzzy player
- More complex to tune
- The search still depends on copy-heavy board handling

### 3. Fuzzy Logic AI

The Fuzzy Logic player is implemented in `ai_fuzzy.py`.

Current characteristics:

- Uses fuzzy membership functions for:
  - material advantage
  - king danger
  - center control
- Scores each legal move using fuzzy-inspired rules
- Chooses from the top few moves with slight randomness

Strengths:

- Very fast
- Easy to experiment with heuristics
- Good for demonstrating rule-based AI ideas

Limitations:

- Less rigorous than search-based methods
- Depends heavily on manually chosen scoring rules
- Not currently connected to the default match loop

## GUI Features

The Pygame interface in `gui.py` currently includes:

- 6x6 board display
- Right-side information panel
- Piece sprites loaded from `assets/pieces/`
- Unicode chess piece fallback if sprites are unavailable
- Move log display
- Board coordinates
- Last move highlighting
- King-in-check highlighting
- Thinking animation while AI is calculating
- Winner screen at the end of the game
- Short move animation for piece movement

## How To Run

### Requirements

- Python 3
- `pygame`

### Install Dependency

```bash
pip install pygame
```

### Run The Game

```bash
python main.py
```

## How To Switch AI Players

Right now, player selection is hardcoded in `main.py`.

Example current section:

```python
white = MinimaxPlayer(color='W', depth=3)
# black = MCTSPlayer(color='B', simulations=800)
black = MinimaxPlayer(color='B', depth=3)
```

You can manually change this block to test different matchups, for example:

### Minimax vs MCTS

```python
white = MinimaxPlayer(color='W', depth=3)
black = MCTSPlayer(color='B', simulations=800)
```

### Minimax vs Fuzzy

```python
from ai_fuzzy import FuzzyPlayer

white = MinimaxPlayer(color='W', depth=3)
black = FuzzyPlayer(color='B')
```

### MCTS vs Fuzzy

```python
from ai_fuzzy import FuzzyPlayer

white = MCTSPlayer(color='W', simulations=800)
black = FuzzyPlayer(color='B')
```

## Known Limitations

The project is functional, but there are still several limitations:

- No automated tests are included
- No `requirements.txt` file is included
- No `.gitignore` file is included
- The GUI labels do not always match the actual player setup
- The main window title still mentions Fuzzy Logic even when Fuzzy is not playing
- The side panel text currently mentions MCTS even when MCTS is not active
- Fuzzy Logic AI is present in the repo but not connected to the default run path
- Many configuration values are hardcoded
- The board logic uses deep copies frequently, which can become expensive
- There is no command-line configuration
- There is no save/load feature
- There is no human vs AI mode yet
- There is no tournament or batch evaluation system yet

## Things That Can Be Improved

The following improvements would make the project stronger technically and easier to present:

### Documentation And Project Hygiene

- Add a `requirements.txt` file
- Add a `.gitignore` file to exclude `__pycache__` and other generated files
- Add docstrings consistently across all files
- Keep comments and GUI labels synchronized with the current code
- Document how to compare AI results formally

### Code Structure

- Move hardcoded constants into a central config file
- Separate game rules, AI logic, and UI logic more cleanly
- Add a shared utility module for repeated constants and helper functions
- Reduce repeated logic across AI files

### Correctness And Reliability

- Add unit tests for each piece's movement rules
- Add tests for check detection
- Add tests for checkmate and stalemate
- Add tests for pawn promotion
- Add tests to verify that illegal self-check moves are rejected

### AI Improvements

- Add a player selection system instead of editing `main.py`
- Add command-line options for:
  - player type
  - search depth
  - number of simulations
  - move delay
- Improve Minimax with:
  - move ordering
  - transposition tables
  - better evaluation tuning
- Improve MCTS with:
  - stronger rollout policy
  - more efficient state reuse
  - better board hashing
- Improve Fuzzy Logic with:
  - more formal membership functions
  - more rules
  - better calibration of scores

### Performance Improvements

- Replace full-board deep copies with faster move/unmove logic
- Cache repeated evaluations when possible
- Profile the slowest sections of the search
- Benchmark AI move times and win rates

### GUI Improvements

- Show the actual active player names automatically
- Add a start menu for selecting AI types
- Add restart and pause controls
- Add speed controls for faster experiments
- Add a board reset option
- Add on-screen statistics such as:
  - move time
  - current turn
  - total moves
  - AI type for each side

### Feature Extensions

- Add human vs AI mode
- Add human vs human mode
- Add AI vs AI tournament mode
- Save match logs to text or CSV
- Export results for analysis in the report
- Add alternate board sizes or alternate rule sets if needed for future research

## Suggested Improvement Priority

If the project is being prepared for submission, demo, or further development, this is a practical order:

1. Add `requirements.txt` and `.gitignore`.
2. Connect all AI agents through one clean player-selection system.
3. Make GUI labels reflect the actual selected players automatically.
4. Add tests for rules and endgame conditions.
5. Improve performance in board copying and search.
6. Add benchmarking and result logging for AI comparison.
7. Add extra features such as human play and tournament mode.

## Summary

This project already has a solid foundation:

- the custom game rules are implemented
- the board engine is working
- three different AI approaches are implemented
- the GUI can visualize automated matches

The biggest remaining work is not building the core game from scratch anymore. The biggest remaining work is improving polish, consistency, testing, configurability, and evaluation so the project becomes easier to present, compare, and extend.

