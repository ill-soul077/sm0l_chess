# Change 1: AI System Improvements for SmoL Chess

This document explains the major AI improvements made to the SmoL Chess project.
It is written so that a teammate, teacher, or project reviewer can understand:

- what the system was doing before
- what was changed
- why the change matters
- how the new version improves performance, quality, and academic value

The changes were made in these files:

- `ai_minimax.py`
- `ai_mcts.py`
- `ai_fuzzy.py`

No required interface change was made to `main.py`. The game loop can still use the AI players in the same way as before.

---

## 1. Minimax Improvements

### 1.1 What the old Minimax system did

Previously, the Minimax player:

- used depth-limited Minimax search
- used alpha-beta pruning
- evaluated positions using:
  - material
  - mobility
  - center control
  - king safety

This was already a good starting point, but it had two important weaknesses:

1. It searched legal moves in the order they were generated.
2. It did not remember previously analyzed board positions.

Because of this:

- alpha-beta pruning was weaker than it could be
- many repeated board states were recalculated again and again
- deeper searches became slower than necessary

---

### 1.2 What was changed in Minimax

Two major upgrades were added:

1. Move ordering
2. Zobrist-hash transposition table

---

### 1.3 Move ordering

#### Previous behavior

Before the change, Minimax explored moves in raw legal-move order.
That means a weak quiet move could be searched before a strong tactical move such as:

- a checkmate
- a promotion
- a capture
- a checking move

This reduces alpha-beta efficiency, because pruning becomes strongest when good moves are searched early.

#### New behavior

Now Minimax gives priority to tactically important moves first.

The search order is:

1. transposition-table preferred move, if available
2. immediate checkmate
3. promotion
4. captures using MVV-LVA style scoring
5. checking moves
6. center-improving moves
7. remaining quiet moves

This is implemented using:

- a `score_move(...)` function
- an `order_moves(...)` function

#### Why this improves the system

Alpha-beta pruning works best when the strongest moves are considered first.
If a strong move is searched early:

- `alpha` rises faster in maximizing nodes
- `beta` falls faster in minimizing nodes
- many weaker branches can be cut off without full search

So the tree does not become smaller in theory, but the effective explored part becomes smaller in practice.

#### Practical effect

The improved Minimax now reaches the same search depth with less waste.
In a depth-4 verification run from the initial board, the new implementation produced:

- `nodes = 2860`
- `cutoffs = 586`
- `tt_hits = 286`

This shows that pruning and caching are now actively helping the search.

---

### 1.4 Transposition table with Zobrist hashing

#### Previous behavior

Previously, if the same board position appeared again through a different move order, Minimax would evaluate it from scratch.

This is inefficient because games often contain transpositions:

- two different sequences of moves
- reaching the same final board state

Without caching, the algorithm repeats work unnecessarily.

#### New behavior

A transposition table was added using Zobrist hashing.

The hash represents the board using:

- piece type
- piece color
- square position
- pawn `has_moved` state
- side to move

Each position is stored in a transposition table with:

- search depth
- score
- node type flag:
  - `EXACT`
  - `LOWERBOUND`
  - `UPPERBOUND`
- best move
- `search_turn_id`

#### Why Zobrist hashing was used

Zobrist hashing is a standard chess-engine technique.
It is academically strong because:

- it is fast
- it is widely used in game AI
- it gives a compact and professional way to identify states

#### Why `search_turn_id` was added

The system keeps the transposition table across turns for performance.
However, exact score reuse across different turns can be risky in repeated positions.

To solve this safely:

- old entries may still provide a move-ordering hint
- exact score reuse is only allowed inside the same root search

This keeps the speed benefit while avoiding unsafe reuse of stale exact values.

#### How it improves the system

The transposition table improves Minimax in two ways:

1. It avoids repeated evaluation of the same board state.
2. It supplies a previously strong move as a hint for future move ordering.

This improves:

- speed
- efficiency
- scalability to deeper searches
- academic quality of the implementation

#### Added reporting support

The new Minimax player now records:

- `nodes`
- `cutoffs`
- `tt_hits`
- `tt_ordering_hits`
- `max_depth`

These are stored in `MinimaxPlayer.last_search_stats`.

This is very useful for:

- performance analysis
- academic discussion
- before/after comparison in the report

---

## 2. MCTS Improvements

### 2.1 What the old MCTS rollout system did

The previous MCTS system already had some improvements compared to a very naive rollout policy.
It included:

- immediate checkmate detection
- promotion preference
- capture preference
- center preference
- tree reuse

However, the rollout policy was still limited because it did not formally model tactical safety.
That means a rollout could still:

- move a valuable piece to a dangerous square
- choose a move that looks active but is actually a blunder
- ignore whether the moved piece becomes hanging

This makes simulations noisier and less realistic.

---

### 2.2 What was changed in MCTS

The rollout policy was upgraded into a lightweight tactical heuristic.

New helper logic was added to evaluate rollout moves using:

- immediate checkmate
- promotion
- capture value
- giving check
- center move
- pawn advance
- whether the moved piece becomes attacked
- whether the moved piece is defended
- whether the move allows obvious tactical loss on the next ply

The rollout policy now uses:

- `rollout_move_score(...)`
- `count_attackers(...)`
- a top-3 move shortlist
- softmax sampling

---

### 2.3 Explicit top-3 softmax sampling

#### Previous behavior

Earlier rollout selection was weighted, but not fully specified in a rigorous academic way.

#### New behavior

Now the rollout policy is clearly defined:

1. Score all legal rollout moves.
2. Keep the top 3 scored moves.
3. Choose one of these using softmax probability:

```text
p_i = exp(score_i / 15) / sum(exp(score_j / 15))
```

The temperature is fixed at:

```text
T = 15
```

#### Why this is better

This gives a strong balance between:

- exploration
- tactical preference

If the temperature were too small, the rollout would become nearly deterministic.
If it were too large, the rollout would become too random.

Using `T = 15` keeps the rollout:

- stochastic enough for Monte Carlo behavior
- informed enough to reduce blunders

In verification sampling from the initial position, different top rollout moves were actually selected, for example:

- `(BN, (2, 2))`
- `(BQ, (2, 2))`
- `(BN, (2, 3))`

This confirms that the rollout is not collapsing to a single greedy move.

---

### 2.4 How the new rollout improves the system

The improved rollout helps MCTS because the quality of Monte Carlo simulation matters.

If rollouts are too random:

- the search receives noisy feedback
- bad moves may look better than they should

If rollouts are slightly smarter:

- simulations better reflect tactical reality
- hanging moves are penalized
- safe captures are preferred
- obviously bad continuations become less likely

This improves:

- move quality
- consistency
- interpretability
- academic credibility

At the same time, the rollout is still lightweight, so MCTS remains practical for a live demo.

---

## 3. Fuzzy Logic Improvements

### 3.1 What the old Fuzzy Logic system did

The previous Fuzzy player used informal rule-based scoring.
It had useful ideas, but it was not fully formal in an academic fuzzy-systems sense.

The old approach:

- used hand-written heuristic values
- mixed fuzzy concepts with direct scoring
- used some randomness in final move selection

This made it harder to explain rigorously in a report.

Main limitations:

- membership functions were not formally defined as triangular or trapezoidal sets
- the system was partly heuristic rather than fully structured
- repeated runs could produce different results

---

### 3.2 What was changed in the Fuzzy system

The Fuzzy player was redesigned as a deterministic Sugeno-style fuzzy system.

The new implementation includes:

- formal triangular membership functions
- formal trapezoidal membership functions
- explicit input universes
- explicit rule firing
- weighted-average output
- deterministic move selection

---

### 3.3 Formal fuzzy input variables

The new Fuzzy system uses these post-move inputs:

1. `post_material_advantage`
2. `king_danger_index`
3. `center_control_count`

It also uses:

- `pre_material_advantage`

This is necessary for the material-recovery rule.

#### Important academic improvement

All fuzzy inputs are now evaluated on the post-move board.

This is a very important correction.
It means the system judges the result of a move, not just the original state.

For example:

- if a move wins material
- the post-move material advantage reflects that improvement

This is much more correct than evaluating fuzzy inputs only before the move.

---

### 3.4 Membership functions

Two standard fuzzy membership types were added:

- `triangular(x, a, b, c)`
- `trapezoidal(x, a, b, c, d)`

These are standard in academic fuzzy systems and make the model easier to explain and defend.

#### Material advantage sets

- disadvantaged
- balanced
- advantaged

#### King danger sets

- safe
- warning
- exposed

#### Center control sets

- weak
- moderate
- strong

This formalizes the old fuzzy ideas into a proper fuzzy inference system.

---

### 3.5 Sugeno-style inference

#### Previous behavior

The old system combined fuzzy concepts and heuristics in a looser way.

#### New behavior

Now the system uses Sugeno-style inference:

- antecedent combination by `min`
- singleton outputs such as:
  - `very_bad = 10`
  - `bad = 30`
  - `neutral = 50`
  - `good = 70`
  - `excellent = 90`
- final crisp score by weighted average

This makes the system:

- structured
- reproducible
- much easier to describe in a formal report

---

### 3.6 Material recovery rule

One important improvement was the handling of recovery when the side is behind in material.

#### Old informal idea

The old system roughly rewarded captures when the player was losing material.

#### New formal rule

Now the rule is:

- if the side is disadvantaged
- and `post_material_advantage > pre_material_advantage`
- then a recovery rule fires with strength equal to the disadvantaged membership

This is better because:

- it is not just a boolean “capture happened” rule
- it measures actual improvement in material advantage
- it stays consistent with the fuzzy framework

This is easier to justify academically.

---

### 3.7 Deterministic move selection

#### Previous behavior

The old Fuzzy player picked from the top few moves with randomness.

This added variety, but it reduced reproducibility.

#### New behavior

The new Fuzzy player is deterministic.
It always chooses the best final score.

Tie-breaking is also deterministic and stable:

1. checkmate
2. promotion
3. capture value
4. check
5. lexical board order

#### Why this improves the system

For academic submission, deterministic behavior is much better because:

- repeated runs give the same result
- comparisons are easier
- the behavior is easier to analyze and explain

In verification, repeated calls from the same initial board returned the same move both times.

---

## 4. Overall System Improvement

### 4.1 How the project improved technically

After these changes:

- Minimax searches more efficiently
- Minimax remembers repeated positions
- MCTS rollouts are more intelligent and less blunder-prone
- Fuzzy Logic is now formally structured and reproducible

This improves the project in three major dimensions:

#### 1. Performance

- fewer wasted Minimax evaluations
- stronger alpha-beta pruning
- more useful MCTS simulations

#### 2. Decision quality

- tactical moves are prioritized in Minimax
- dangerous rollout moves are penalized in MCTS
- Fuzzy decisions are based on more formal post-move reasoning

#### 3. Academic quality

- Zobrist hashing is a strong standard technique
- softmax rollout selection is explicitly defined
- fuzzy sets are formally modeled
- deterministic output improves reproducibility
- Minimax statistics can be reported directly

---

## 5. Verification Summary

The updated system was checked with practical smoke tests.

### Minimax

- returned legal moves
- recorded search statistics
- showed real transposition-table hits at depth 4

Example:

```text
nodes = 2860
cutoffs = 586
tt_hits = 286
tt_ordering_hits = 286
max_depth = 4
```

### MCTS

- returned legal moves
- rollout selection produced multiple different top moves
- top-3 softmax behavior remained stochastic

### Fuzzy Logic

- returned legal moves
- produced deterministic repeated outputs from the same board

---

## 6. Why these changes matter for submission and demo

For academic submission, these changes make the project more defendable because the AI methods are now:

- more formal
- more efficient
- more measurable
- easier to compare

For the live demo, these changes make the system more impressive because:

- Minimax is smarter and faster
- MCTS behaves less randomly
- Fuzzy Logic behaves consistently and can be explained clearly

So these changes do not just add complexity.
They make the whole project more mature, more stable, and more suitable for presentation to teachers and reviewers.

---

## 7. Final Short Summary

In simple terms:

- Minimax now searches smarter and remembers repeated states.
- MCTS now simulates smarter and avoids more tactical mistakes.
- Fuzzy Logic is now a proper formal fuzzy system instead of an informal heuristic scorer.

Together, these changes significantly improve both the technical quality and the academic value of SmoL Chess.

