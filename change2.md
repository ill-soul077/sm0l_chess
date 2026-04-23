# Change 2: Performance and GUI Improvements for SmoL Chess

This file explains the second major set of improvements made to the SmoL Chess project.

The main goals of these changes were:

- improve performance in the board engine
- remove hardcoded AI selection from the game loop
- make the GUI more polished and easier to understand during a live demo
- make the system clearer for academic presentation

The changes were made mainly in:

- `board.py`
- `ai_minimax.py`
- `ai_mcts.py`
- `ai_fuzzy.py`
- `main.py`
- `gui.py`

---

## 1. Performance Improvement: Board Apply/Undo Refactor

### 1.1 What the old system did

Previously, the board engine used:

- `copy.deepcopy(board)`

inside `apply_move()`.

That means every time the AI wanted to test a possible move, the system:

1. copied the full 6x6 board
2. copied every piece object
3. applied the move on the copied board

This approach is simple, but it becomes expensive when search is deep.

This especially hurts:

- Minimax
- legal move filtering
- MCTS rollouts

because these systems simulate many moves repeatedly.

---

### 1.2 What was changed

The board engine was refactored to use:

- `apply_move(board, piece, dest)`
- `undo_move(board, undo_token)`

instead of cloning the board on every test.

Now:

- `apply_move()` changes the current board directly
- it returns an undo token
- `undo_move()` restores the board exactly to the previous state

This token stores:

- the moving piece
- source square
- destination square
- captured piece if one existed
- previous pawn `has_moved` state
- promotion information

### 1.3 Important rule note

The project still has:

- no castling
- no en-passant

So the undo token does not include fields for those rules.
That is intentional and correct for this mini-chess version.

---

### 1.4 Why this improves performance

This change improves performance because:

- `deepcopy` clones the whole board every time
- `apply/undo` changes only the few objects involved in the move

So instead of rebuilding a full board repeatedly, the engine:

- applies the move
- checks the result
- undoes the move

This reduces:

- memory allocation
- object creation overhead
- board-copy overhead

In practice, this makes Minimax and move legality checking much more efficient.

---

### 1.5 Additional helper: `copy_board()`

A new helper was also added:

- `copy_board(board)`

This is used only when the system truly needs an independent board snapshot.

That is especially useful for:

- MCTS tree nodes

This is much cleaner than using `deepcopy()` everywhere.

It also makes the design easier to explain:

- use `apply/undo` for fast temporary simulation
- use `copy_board()` only for stable saved board states

---

## 2. AI Integration with the New Board System

### 2.1 Minimax

Minimax was updated to use the new in-place move pattern.

Before:

- it created a new board for every recursive child state

Now:

- it applies a move
- recursively searches the same board object
- undoes the move afterward

This keeps:

- move ordering
- alpha-beta pruning
- Zobrist hashing
- transposition table support

while reducing simulation overhead.

So Minimax becomes faster without changing its decision logic.

---

### 2.2 MCTS

MCTS was also updated to stop relying on `deepcopy()`.

The chosen method is:

- `copy_board() + one apply_move()`

This is used when creating child nodes.

Why this method was chosen:

- it is simpler
- it is safer
- each MCTS node gets its own stable board snapshot

At the same time, rollout analysis now uses:

- `apply_move()`
- `undo_move()`

inside the rollout logic itself.

So MCTS now uses:

- explicit snapshots only for node storage
- fast apply/undo for short temporary simulations

This is cleaner and more efficient than using general-purpose deep copies everywhere.

---

### 2.3 Fuzzy Logic

The Fuzzy player was also adapted to the new board model.

Before:

- it relied on post-move copied boards

Now:

- it applies a move in place
- computes post-move features
- undoes the move

This preserves the same fuzzy decision logic, but makes evaluation more efficient.

---

## 3. GUI Improvement: Start Menu for AI Selection

### 3.1 What the old system did

Previously, `main.py` hardcoded the players before the game started.

For example:

- White = Minimax
- Black = MCTS

If the user wanted to change the match, they had to edit the code manually.

This was inconvenient for:

- demos
- experiments
- teacher presentation
- teammate use

---

### 3.2 What was changed

A real Pygame start menu was added.

Now, before the match begins, the user can choose:

- White AI type
- Black AI type

Supported options:

- Minimax
- MCTS
- Fuzzy Logic

Defaults:

- White = Minimax
- Black = MCTS

---

### 3.3 How the menu improves the system

This improves the project because:

- the game is now interactive before the match starts
- match setup is easier
- no code editing is needed just to compare AIs
- the project feels more complete and polished

This is especially useful in a live demo because the teacher or audience can see that:

- the project supports multiple AI agents
- the matchup is chosen dynamically
- the system is more than a hardcoded prototype

---

### 3.4 Menu design quality

The menu was designed to feel visually connected to the main game.

It uses:

- the chess piece PNG assets from `assets/pieces/`
- polished AI selection cards
- hover effects
- selected state highlights
- a central start button
- keyboard and mouse input

This makes the menu easier to use and more professional in presentation.

---

## 4. GUI Improvement: Dynamic Window Title and Side Panel

### 4.1 What the old system did

Previously, the GUI displayed hardcoded text like:

- fixed window title
- fixed White AI label
- fixed Black AI label

This caused inconsistency when the actual players changed.

For example:

- the code might run Minimax vs MCTS
- but the title or side panel could still mention something else

That is confusing for reviewers and teammates.

---

### 4.2 What was changed

The GUI now stores live match metadata and updates it dynamically.

The window title now shows:

```text
SmoL Chess — {white_player.name} vs {black_player.name}
```

The side panel now shows:

- White player name
- Black player name
- White AI type
- Black AI type

This means the visible interface always matches the actual running match.

---

### 4.3 Why this improves the system

This improves clarity because:

- the GUI now tells the truth about the active game
- the interface is easier to understand during a demo
- no mismatch happens between code behavior and displayed text

This is a big presentation improvement, even though it is not part of the game rules.

---

## 5. GUI Improvement: Live On-Screen Match Stats

### 5.1 What was added

The side panel now includes a live stats section showing:

- move number
- current turn
- last move time
- White AI type
- Black AI type

If no move has completed yet, the panel shows:

- `Last Move Time: ---`

instead of trying to format a missing value.

---

### 5.2 Why the stats panel matters

This improves the system in several ways.

#### For demos

It helps the audience immediately see:

- whose turn it is
- how fast the AIs are moving
- what kind of AI is controlling each side

#### For academic presentation

It gives more visible evidence that:

- different AI methods are active
- the system tracks runtime information
- AI comparison is part of the project design

#### For debugging and testing

It makes it easier to notice:

- unusually slow turns
- whether the correct AI is playing
- whether the match is progressing correctly

---

## 6. Safety Improvement: Threaded Search on a Board Snapshot

### 6.1 Why this became necessary

After changing the board engine to in-place `apply/undo`, the AI search can no longer safely run on the exact same board object that the GUI is drawing from in another thread.

If it did, the GUI might try to draw the board while the AI is temporarily modifying it during search.

That could cause:

- flickering
- inconsistent rendering
- hard-to-debug race conditions

---

### 6.2 What was changed

The AI worker now receives:

- `copy_board(board)`

before searching.

This means:

- the GUI keeps drawing the real live game board
- the AI searches on its own private snapshot

So the system keeps:

- the performance benefit of `apply/undo`
- safe background-thread behavior

This is an important engineering improvement.

---

## 7. Verification Summary

After these changes, the system should be checked in the following ways:

### Board verification

- apply a move and undo it
- verify the original board is restored
- test capture undo
- test pawn first-move undo
- test promotion undo

### AI verification

- Minimax still returns legal moves
- MCTS still returns legal moves
- Fuzzy still returns legal moves
- MCTS works without `deepcopy`
- Minimax benefits from the faster board simulation model

### GUI verification

- start menu appears before the game starts
- both White and Black can be configured independently
- keyboard and mouse selection both work
- title matches selected players
- side panel shows the correct AI names and types
- last move time shows `---` before move 1 and time values afterward
- piece assets appear in the menu and side panel

---

## 8. Why These Changes Matter Overall

These changes improve the project in three major ways.

### 1. Performance

- less board-copy overhead
- faster temporary simulation
- cleaner board state handling

### 2. Usability

- no need to edit code to change matchups
- better interface before and during the game
- clearer visual information for the user

### 3. Academic and Demo Quality

- more professional presentation
- stronger explanation of performance design
- better support for comparing AI methods in front of a teacher or audience

---

## 9. Final Short Summary

In simple terms:

- the board engine is now faster because it uses apply/undo instead of deep copying
- the game now starts with a proper AI selection menu
- the GUI now correctly shows the real active AI names and match statistics

Together, these changes make SmoL Chess faster, cleaner, easier to demonstrate, and easier to explain in an academic setting.

