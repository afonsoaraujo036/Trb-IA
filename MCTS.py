"""
Monte Carlo Tree Search (MCTS) for PopOut
==========================================

Three variants:
  MCTS          – standard UCT, random rollout
  MCTSHeuristic – UCT + heuristic rollout (win/block/score) + tree reuse
  MCTSTopK      – UCT + Top-K expansion + heuristic rollout + tree reuse

wins/visits perspective
-----------------------
Each node stores wins from the perspective of its PARENT player —
the player who chose to transition INTO this node.

  • select_child → max(child.wins/visits)   [parent's view, so just maximise]
  • simulate     → score measured for parent.state.current_player
  • backpropagate(result): this node += result; parent += (1-result)
"""

import math
import time
import random
import copy
from PopOut import PopOutState, PLAYER_1, PLAYER_2, ROWS, COLS


# ─────────────────────────────────────────────────────────────────────────────
# Static board evaluation
# ─────────────────────────────────────────────────────────────────────────────

def _window_score(window, player, opponent):
    pc = window.count(player)
    oc = window.count(opponent)
    ec = window.count(0)
    if oc > 0:
        return 0
    if pc == 4: return 10000
    if pc == 3 and ec == 1: return 50
    if pc == 2 and ec == 2: return 5
    return 0


def _all_windows(board):
    for r in range(ROWS):
        for c in range(COLS - 3):
            yield [board[r][c + i] for i in range(4)]
    for c in range(COLS):
        for r in range(ROWS - 3):
            yield [board[r + i][c] for i in range(4)]
    for r in range(ROWS - 3):
        for c in range(COLS - 3):
            yield [board[r + i][c + i] for i in range(4)]
    for r in range(ROWS - 3):
        for c in range(3, COLS):
            yield [board[r + i][c - i] for i in range(4)]


def evaluate_state(state, player):
    """Positive = good for player, negative = good for opponent."""
    opponent = PLAYER_2 if player == PLAYER_1 else PLAYER_1
    score = 0
    for w in _all_windows(state.board):
        score += _window_score(w, player, opponent)
        score -= _window_score(w, opponent, player)
    mid = COLS // 2
    for r in range(ROWS):
        if state.board[r][mid] == player:
            score += 3
    return score


# ─────────────────────────────────────────────────────────────────────────────
# Opponent threat simulation helper
# ─────────────────────────────────────────────────────────────────────────────

def _opponent_wins_after(state_after_our_move):
    """
    Given a state where it is the OPPONENT's turn,
    returns True if the opponent has any immediate winning move.
    """
    opponent = state_after_our_move.current_player
    for om in state_after_our_move.get_valid_moves():
        if state_after_our_move.make_move(om).get_winner() == opponent:
            return True
    return False

def _is_dangerous_pop(state, move):
    """
    Detect if a POP move creates tactical danger.
    """
    if move[0] != 'pop':
        return False

    current = state.current_player
    opponent = PLAYER_2 if current == PLAYER_1 else PLAYER_1

    ns = state.make_move(move)

    # 1. Immediate opponent win
    for om in ns.get_valid_moves():
        if ns.make_move(om).get_winner() == opponent:
            return True

    # 2. Opponent fork detection
    for om in ns.get_valid_moves():
        nns = ns.make_move(om)

        wins = 0
        for oom in nns.get_valid_moves():
            if nns.make_move(oom).get_winner() == opponent:
                wins += 1

        if wins >= 2:
            return True

    # 3. Huge positional swing
    if evaluate_state(ns, opponent) >= 80:
        return True

    return False


def _make_opponent_state(state):
    """
    Build a temporary state where it is the OPPONENT's turn to move,
    with everything else identical.  Used to probe opponent winning moves.
    """
    opponent = PLAYER_2 if state.current_player == PLAYER_1 else PLAYER_1
    return PopOutState(
        state.board, opponent,
        state.last_move, state.last_move_type,
        state.state_history
    )


# ─────────────────────────────────────────────────────────────────────────────
# Forced-move layer (called before MCTS search)
# ─────────────────────────────────────────────────────────────────────────────

def find_immediate_tactical_move(state):
    """
    Returns a move without MCTS search when the answer is clearly forced:

      1. Immediate win for us.
      2. Block opponent's immediate win — iterate over THEIR moves,
         not ours (this was the classic wrong-player bug).
      3. Avoid giving opponent an immediate win on the very next turn
         (2-ply safety filter).
      4. Fork creation: after our move, ≥2 of our follow-ups are wins
         regardless of what the opponent does.
      5. Fork blocking: prevent the opponent from creating a fork.

    Returns None to hand off to MCTS.
    """
    current  = state.current_player
    opponent = PLAYER_2 if current == PLAYER_1 else PLAYER_1
    moves    = state.get_valid_moves()
    if not moves:
        return None

    # ── 1. Win immediately ────────────────────────────────────────────────────
    for m in moves:
        if state.make_move(m).get_winner() == current:
            return m

    # ── 2. Block opponent's immediate win ────────────────────────────────────
    # CORRECT: simulate opponent's moves from a flipped board, not our moves.
    opp_state = _make_opponent_state(state)
    for opp_move in opp_state.get_valid_moves():
        if opp_state.make_move(opp_move).get_winner() == opponent:
            # Opponent wins with opp_move → try to occupy/prevent that column
            target_col = opp_move[1]
            # Prefer same move-type (drop→drop, pop→pop) in same column
            for m in moves:
                if m[1] == target_col and m[0] == opp_move[0]:
                    return m
            # Fallback: any move in that column
            for m in moves:
                if m[1] == target_col:
                    return m

    # ── 3. Avoid handing opponent an immediate win next turn ──────────────────
    safe_moves = []

    for m in moves:
        ns = state.make_move(m)

        if _opponent_wins_after(ns):
            continue

        # Extra protection for POP moves
        if _is_dangerous_pop(state, m):
            continue

        safe_moves.append(m)

    if not safe_moves:
        # All moves hand the opponent a win — pick the one that maximises our eval
        scored = [(m, evaluate_state(state.make_move(m), current)) for m in moves]
        return max(scored, key=lambda x: x[1])[0]

    # If only one safe move exists, play it directly
    if len(safe_moves) == 1:
        return safe_moves[0]

    # ── 4. Fork: after our move, ≥2 winning follow-ups for us (ignoring opp) ─
    for m in safe_moves:
        ns = state.make_move(m)   # opponent's turn
        our_wins = sum(1 for wm in ns.get_valid_moves()
                       if ns.make_move(wm).get_winner() == current)
        if our_wins >= 2:
            return m

    # ── 5. Block opponent's dangerous 2-move threats ─────────────────────────
    # Detect columns where playing there gives the opponent 3-in-a-row (open),
    # which leads to a forced win 1 move later.
    # We do this by simulating every opponent move and scoring the resulting board.
    threat_cols = set()
    opp_state2 = _make_opponent_state(state)
    for opp_move in opp_state2.get_valid_moves():
        ns_opp = opp_state2.make_move(opp_move)
        opp_score = evaluate_state(ns_opp, opponent)
        if opp_score >= 50:   # opponent gains a 3-in-a-row open threat
            threat_cols.add(opp_move[1])

    if threat_cols:
        # Try to block those columns with a safe move
        blocking = [m for m in safe_moves if m[1] in threat_cols]
        if blocking:
            scored = [(m, evaluate_state(state.make_move(m), current)) for m in blocking]
            best_block = max(scored, key=lambda x: x[1])[0]
            return best_block

    # ── 6. Block opponent fork ────────────────────────────────────────────────
    non_fork_moves = []
    for m in safe_moves:
        ns        = state.make_move(m)   # opponent's turn
        opp_forks = False
        for om in ns.get_valid_moves():
            nns      = ns.make_move(om)  # our turn
            opp_wins = sum(1 for wm in nns.get_valid_moves()
                           if nns.make_move(wm).get_winner() == opponent)
            if opp_wins >= 2:
                opp_forks = True
                break
        if not opp_forks:
            non_fork_moves.append(m)

    pool = non_fork_moves if non_fork_moves else safe_moves
    # Force a move only when pool == 1; otherwise let MCTS decide with context
    if len(pool) == 1:
        return pool[0]

    return None   # hand off to MCTS


# ─────────────────────────────────────────────────────────────────────────────
# Heuristic rollout move picker
# ─────────────────────────────────────────────────────────────────────────────

def _heuristic_pick(state, moves):
    """
    Used inside rollouts. Same priority as find_immediate_tactical_move
    but lightweight (no fork detection — too slow for per-step rollout).

      1. Immediate win
      2. Block opponent's immediate win  (correct: iterate OPPONENT moves)
      3. Avoid giving opponent immediate win on reply
      4. Best by static eval
    """
    current  = state.current_player
    opponent = PLAYER_2 if current == PLAYER_1 else PLAYER_1

    # 1. Win
    for move in moves:
        if state.make_move(move).get_winner() == current:
            return move

    # 2. Block — iterate over OPPONENT's moves
    opp_state = _make_opponent_state(state)
    blocking_cols = set()
    for opp_move in opp_state.get_valid_moves():
        if opp_state.make_move(opp_move).get_winner() == opponent:
            blocking_cols.add(opp_move[1])
    for move in moves:
        if move[1] in blocking_cols:
            return move

    # 3. Avoid giving opponent immediate win
    safe = []
    for move in moves:
        ns = state.make_move(move)

        if _opponent_wins_after(ns):
            continue

        if _is_dangerous_pop(state, move):
            continue

    safe.append((move, evaluate_state(ns, current)))

    if safe:
        # 4. Among safe moves, block opponent 2-move threats first
        threat_cols = set()
        opp_state2 = _make_opponent_state(state)
        for opp_move in opp_state2.get_valid_moves():
            ns_opp = opp_state2.make_move(opp_move)
            if evaluate_state(ns_opp, opponent) >= 50:
                threat_cols.add(opp_move[1])

        if threat_cols:
            blocking = [(m, s) for m, s in safe if m[1] in threat_cols]
            if blocking:
                return max(blocking, key=lambda x: x[1])[0]

        return max(safe, key=lambda x: x[1])[0]

    # 5. All dangerous — least bad
    scored = [(m, evaluate_state(state.make_move(m), current)) for m in moves]
    return max(scored, key=lambda x: x[1])[0]


# ─────────────────────────────────────────────────────────────────────────────
# Rollout helpers
# ─────────────────────────────────────────────────────────────────────────────

_MAX_DEPTH = 60


def _score_terminal(end_state, player):
    w = end_state.get_winner()
    if   w == player:    return 1.0
    elif w in (-1, 0):   return 0.5
    else:                return 0.0


def _simulate_heuristic(state, scorer):
    s = copy.deepcopy(state)
    for _ in range(_MAX_DEPTH):
        if s.is_game_over(): break
        moves = s.get_valid_moves()
        if not moves: break
        s = s.make_move(_heuristic_pick(s, moves))
    return _score_terminal(s, scorer)


def _simulate_random(state, scorer):
    s = copy.deepcopy(state)
    for _ in range(_MAX_DEPTH):
        if s.is_game_over(): break
        moves = s.get_valid_moves()
        if not moves: break
        s = s.make_move(random.choice(moves))
    return _score_terminal(s, scorer)


# ─────────────────────────────────────────────────────────────────────────────
# MCTS Node
# ─────────────────────────────────────────────────────────────────────────────

class MCTSNode:
    """
    wins/visits stored from the perspective of the PARENT player.
    """

    def __init__(self, state, parent=None, move=None):
        self.state         = state
        self.parent        = parent
        self.move          = move
        self.children      = []
        self.visits        = 0
        self.wins          = 0.0
        self.untried_moves = state.get_valid_moves()

    def uct_value(self, c=math.sqrt(2)):
        if self.visits == 0:
            return float('inf')
        return (self.wins / self.visits) + c * math.sqrt(
            math.log(self.parent.visits) / self.visits)

    def select_child(self, c=math.sqrt(2)):
        return max(self.children, key=lambda ch: ch.uct_value(c))

    def expand(self):
        if not self.untried_moves:
            return None
        # Centre-priority ordering on expansion
        self.untried_moves.sort(key=lambda m: abs(m[1] - COLS // 2))
        move  = self.untried_moves.pop(0)
        child = MCTSNode(self.state.make_move(move), parent=self, move=move)
        self.children.append(child)
        return child

    def expand_k(self, k):
        self.untried_moves.sort(key=lambda m: abs(m[1] - COLS // 2))
        new_children = []
        for _ in range(min(k, len(self.untried_moves))):
            move  = self.untried_moves.pop(0)
            child = MCTSNode(self.state.make_move(move), parent=self, move=move)
            self.children.append(child)
            new_children.append(child)
        return new_children

    def parent_player(self):
        if self.parent is not None:
            return self.parent.state.current_player
        return self.state.current_player

    def simulate_random(self):
        return _simulate_random(self.state, self.parent_player())

    def simulate_heuristic(self):
        return _simulate_heuristic(self.state, self.parent_player())

    def backpropagate(self, result):
        """result is for THIS node's parent player."""
        self.visits += 1
        self.wins   += result
        if self.parent:
            self.parent.backpropagate(1.0 - result)

    def is_fully_expanded(self):
        return len(self.untried_moves) == 0

    def has_children(self):
        return len(self.children) > 0

    def child_for_move(self, move):
        for ch in self.children:
            if ch.move == move:
                return ch
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Shared best-move selector
# ─────────────────────────────────────────────────────────────────────────────

def _best_move(root):
    """Robust child: most-visited."""
    if not root.children:
        valid = root.state.get_valid_moves()
        return (random.choice(valid) if valid else None), 0.0
    best     = max(root.children, key=lambda ch: ch.visits)
    win_rate = best.wins / best.visits if best.visits > 0 else 0.0
    return best.move, win_rate


# ─────────────────────────────────────────────────────────────────────────────
# Tree-reuse helper
# ─────────────────────────────────────────────────────────────────────────────

def _advance_root(root, move):
    child = root.child_for_move(move)
    if child is not None:
        child.parent = None
        return child
    new_state = root.state.make_move(move)
    return MCTSNode(new_state)


def _match_root(cached_root, root_state):
    """Return cached root if it matches root_state, else a fresh node."""
    if cached_root is None:
        return MCTSNode(root_state)
    try:
        if cached_root.state.get_state_key() == root_state.get_state_key():
            return cached_root
    except Exception:
        pass
    return MCTSNode(root_state)


# ─────────────────────────────────────────────────────────────────────────────
# Variant 1 – Standard MCTS (random rollout)
# ─────────────────────────────────────────────────────────────────────────────

class MCTS:
    name = "Standard MCTS"

    def __init__(self, exploration_constant=1.2,
                 max_simulations=5000, max_time=5.0):
        self.c               = exploration_constant
        self.max_simulations = max_simulations
        self.max_time        = max_time
        self._root           = None

    def search(self, root_state):
        move = find_immediate_tactical_move(root_state)
        if move is not None:
            self._root = None
            return move, 1.0

        root  = _match_root(self._root, root_state)
        start = time.time()
        sims  = 0

        while time.time() - start < self.max_time and sims < self.max_simulations:
            node = root
            while node.has_children() and node.is_fully_expanded():
                node = node.select_child(self.c)
            if not node.state.is_game_over() and node.untried_moves:
                node = node.expand()
                if node is None:
                    continue
            result = node.simulate_random()
            node.backpropagate(result)
            sims += 1

        self._root = root
        return _best_move(root)

    def get_best_move(self, state):
        move, _ = self.search(state)
        return move

    def advance(self, move):
        if self._root is not None:
            self._root = _advance_root(self._root, move)


# ─────────────────────────────────────────────────────────────────────────────
# Variant 2 – Heuristic rollout MCTS + tree reuse
# ─────────────────────────────────────────────────────────────────────────────

class MCTSHeuristic(MCTS):
    """UCT + 2-ply aware heuristic rollout + persistent tree reuse."""

    name = "MCTS + Heuristic Rollout"

    def search(self, root_state):
        move = find_immediate_tactical_move(root_state)
        if move is not None:
            self._root = None
            return move, 1.0

        root  = _match_root(self._root, root_state)
        start = time.time()
        sims  = 0

        while time.time() - start < self.max_time and sims < self.max_simulations:
            node = root
            while node.has_children() and node.is_fully_expanded():
                node = node.select_child(self.c)
            if not node.state.is_game_over() and node.untried_moves:
                node = node.expand()
                if node is None:
                    continue
            result = node.simulate_heuristic()
            node.backpropagate(result)
            sims += 1

        self._root = root
        return _best_move(root)


# ─────────────────────────────────────────────────────────────────────────────
# Variant 3 – Top-K MCTS + tree reuse
# ─────────────────────────────────────────────────────────────────────────────

class MCTSTopK(MCTS):
    """Expands K children per iteration + heuristic rollout + tree reuse."""

    name = "MCTS Top-K"

    def __init__(self, k=3, exploration_constant=1.2,
                 max_simulations=5000, max_time=5.0):
        super().__init__(exploration_constant, max_simulations, max_time)
        self.k    = k
        self.name = f"MCTS Top-{k}"

    def search(self, root_state):
        move = find_immediate_tactical_move(root_state)
        if move is not None:
            self._root = None
            return move, 1.0

        root  = _match_root(self._root, root_state)
        start = time.time()
        sims  = 0

        while time.time() - start < self.max_time and sims < self.max_simulations:
            node = root
            while node.has_children() and node.is_fully_expanded():
                node = node.select_child(self.c)
            if not node.state.is_game_over() and node.untried_moves:
                for child in node.expand_k(self.k):
                    child.backpropagate(child.simulate_heuristic())
                    sims += 1
            else:
                node.backpropagate(node.simulate_heuristic())
                sims += 1

        self._root = root
        return _best_move(root)


# ─────────────────────────────────────────────────────────────────────────────
# Utilities
# ─────────────────────────────────────────────────────────────────────────────

def run_games(mcts1, mcts2, n_games=20, verbose=False):
    p1_wins = p2_wins = draws = 0
    for g in range(n_games):
        state  = PopOutState()
        agents = {PLAYER_1: mcts1, PLAYER_2: mcts2}
        for a in agents.values():
            a._root = None
        while not state.is_game_over():
            cp   = state.get_current_player()
            move = agents[cp].get_best_move(state)
            if move is None:
                break
            for a in agents.values():
                a.advance(move)
            state = state.make_move(move)
        w = state.get_winner()
        if   w == PLAYER_1: p1_wins += 1
        elif w == PLAYER_2: p2_wins += 1
        else:               draws   += 1
        if verbose:
            print(f"  Game {g+1}/{n_games}: winner={w}")
    total = p1_wins + p2_wins + draws
    return {'p1_wins': p1_wins, 'p2_wins': p2_wins, 'draws': draws,
            'p1_win_rate': p1_wins / total if total else 0.0}


def search_convergence(mcts_class, root_state, checkpoints, **kwargs):
    results = []
    for n in checkpoints:
        agent = mcts_class(max_simulations=n, max_time=9999, **kwargs)
        _, wr = agent.search(root_state)
        results.append((n, wr))
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Self-test
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n=== MCTS self-test ===\n")

    # Exact scenario reported by user: P1 plays col4,col6,col5 → P2 must not pop4
    board = [
        [0,0,0,0,0,0,0],[0,0,0,0,0,0,0],[0,0,0,0,0,0,0],
        [0,0,0,0,0,0,0],[0,0,0,2,1,0,0],[0,0,0,1,2,1,0],
    ]
    # It is P2's turn; P2 must NOT play pop(4) because that creates X_XXX → P1 wins
    threat_state = PopOutState(board, PLAYER_2)
    print("Threat board (P2 must not pop col4 — it gifts P1 a win):")
    threat_state.display_board()
    print(f"  find_immediate_tactical_move → "
          f"{find_immediate_tactical_move(threat_state)}")
    for cls in [MCTS, MCTSHeuristic]:
        a = cls(max_simulations=800, max_time=2.0)
        move, wr = a.search(threat_state)
        bad = " ← BUG" if move == ('pop', 4) else " ✓"
        print(f"  {cls.name}: {move}  wr={wr:.3f}{bad}")

    print()
    # Classic block test: P1 has 3 in a row, P2 must block col3
    board2 = [
        [0,0,0,0,0,0,0],[0,0,0,0,0,0,0],[0,0,0,0,0,0,0],
        [0,0,0,0,0,0,0],[0,0,0,0,0,0,0],[1,1,1,0,0,0,0],
    ]
    block_state = PopOutState(board2, PLAYER_2)
    print("Block test (P2 must block col3):")
    block_state.display_board()
    for cls in [MCTS, MCTSHeuristic]:
        a = cls(max_simulations=800, max_time=2.0)
        move, wr = a.search(block_state)
        ok = "✓" if move == ('drop', 3) else "✗"
        print(f"  {cls.name}: {move}  wr={wr:.3f}  {ok}")
