"""
Monte Carlo Tree Search (MCTS) Implementation for PopOut

Three variants:
  - MCTS          : Standard UCT, random rollout, 1 expansion per iteration
  - MCTSHeuristic : UCT with heuristic rollout (win/block detection)
  - MCTSTopK      : UCT with Top-K simultaneous expansions per iteration

Utility:
  - run_games()            : play N games between two MCTS configs, return win rates
  - search_convergence()   : sample win rate at multiple simulation checkpoints
"""

import math
import time
import random
import copy
from PopOut import PopOutState, PLAYER_1, PLAYER_2


# ---------------------------------------------------------------------------
# MCTS Node
# ---------------------------------------------------------------------------

class MCTSNode:
    """Node in the MCTS tree for PopOut game."""

    def __init__(self, state, parent=None, move=None):
        self.state = state
        self.parent = parent
        self.move = move
        self.children = []
        self.visits = 0
        self.wins = 0
        self.untried_moves = state.get_valid_moves()

    def uct_value(self, c=math.sqrt(2)):
        if self.visits == 0:
            return float('inf')
        return (self.wins / self.visits) + c * math.sqrt(math.log(self.parent.visits) / self.visits)

    def select_child(self, c=math.sqrt(2)):
        return max(self.children, key=lambda ch: ch.uct_value(c))

    def expand(self):
        """Expand one random untried child. Returns new child node."""
        if not self.untried_moves:
            return None
        move = random.choice(self.untried_moves)
        self.untried_moves.remove(move)
        child = MCTSNode(self.state.make_move(move), parent=self, move=move)
        self.children.append(child)
        return child

    def expand_k(self, k):
        """Expand up to k untried children. Returns list of new children."""
        new_children = []
        for _ in range(min(k, len(self.untried_moves))):
            move = random.choice(self.untried_moves)
            self.untried_moves.remove(move)
            child = MCTSNode(self.state.make_move(move), parent=self, move=move)
            self.children.append(child)
            new_children.append(child)
        return new_children

    def simulate_random(self, max_depth=50):
        """Random rollout from current node state."""
        state = copy.deepcopy(self.state)
        player_at_node = self.state.get_current_player()
        for _ in range(max_depth):
            if state.is_game_over():
                break
            moves = state.get_valid_moves()
            if not moves:
                break
            state = state.make_move(random.choice(moves))
        return self._result(state, player_at_node)

    def simulate_heuristic(self, max_depth=50):
        """
        Heuristic rollout: prefer immediate winning moves, then blocking moves,
        otherwise random. This dramatically improves simulation quality.
        """
        state = copy.deepcopy(self.state)
        player_at_node = self.state.get_current_player()
        for _ in range(max_depth):
            if state.is_game_over():
                break
            moves = state.get_valid_moves()
            if not moves:
                break
            chosen = self._heuristic_pick(state, moves)
            state = state.make_move(chosen)
        return self._result(state, player_at_node)

    @staticmethod
    def _heuristic_pick(state, moves):
        """Pick winning move > blocking move > random."""
        current = state.get_current_player()
        opponent = state.get_opponent()
        # Check for immediate win
        for move in moves:
            ns = state.make_move(move)
            if ns.get_winner() == current:
                return move
        # Check for opponent win to block
        for move in moves:
            ns = state.make_move(move)
            if ns.get_winner() == opponent:
                return move
        return random.choice(moves)

    @staticmethod
    def _result(end_state, player_at_node):
        winner = end_state.get_winner()
        if winner == player_at_node:
            return 1.0
        elif winner is None:
            return 0.5
        else:
            return 0.0

    def backpropagate(self, result):
        self.visits += 1
        self.wins += result
        if self.parent:
            self.parent.backpropagate(1.0 - result)

    def is_fully_expanded(self):
        return len(self.untried_moves) == 0

    def has_children(self):
        return len(self.children) > 0


# ---------------------------------------------------------------------------
# Variant 1 — Standard MCTS (random rollout, 1 expansion per step)
# ---------------------------------------------------------------------------

class MCTS:
    """Standard UCT MCTS with random rollout."""

    name = "Standard MCTS"

    def __init__(self, exploration_constant=math.sqrt(2), max_simulations=500, max_time=1.0):
        self.c = exploration_constant
        self.max_simulations = max_simulations
        self.max_time = max_time

    def search(self, root_state):
        """
        Run MCTS from root_state.
        Returns (best_move, win_rate).
        """
        root = MCTSNode(root_state)
        start = time.time()
        sims = 0

        while time.time() - start < self.max_time and sims < self.max_simulations:
            node = root
            # Selection
            while node.has_children() and node.is_fully_expanded():
                node = node.select_child(self.c)
            # Expansion
            if not node.state.is_game_over() and node.untried_moves:
                node = node.expand()
                if node is None:
                    continue
            # Simulation
            result = node.simulate_random()
            # Backpropagation
            node.backpropagate(result)
            sims += 1

        if not root.children:
            valid = root_state.get_valid_moves()
            return (random.choice(valid) if valid else None), 0.0

        best = max(root.children, key=lambda ch: ch.visits)
        win_rate = best.wins / best.visits if best.visits > 0 else 0.0
        return best.move, win_rate

    def get_best_move(self, state):
        move, _ = self.search(state)
        return move


# ---------------------------------------------------------------------------
# Variant 2 — Heuristic rollout MCTS
# ---------------------------------------------------------------------------

class MCTSHeuristic(MCTS):
    """
    MCTS with heuristic rollout: prefers immediate wins and blocks over
    random play. Same tree policy as standard MCTS, better simulation quality.
    """

    name = "MCTS + Heuristic Rollout"

    def search(self, root_state):
        root = MCTSNode(root_state)
        start = time.time()
        sims = 0

        while time.time() - start < self.max_time and sims < self.max_simulations:
            node = root
            while node.has_children() and node.is_fully_expanded():
                node = node.select_child(self.c)
            if not node.state.is_game_over() and node.untried_moves:
                node = node.expand()
                if node is None:
                    continue
            result = node.simulate_heuristic()   # <-- key difference
            node.backpropagate(result)
            sims += 1

        if not root.children:
            valid = root_state.get_valid_moves()
            return (random.choice(valid) if valid else None), 0.0

        best = max(root.children, key=lambda ch: ch.visits)
        win_rate = best.wins / best.visits if best.visits > 0 else 0.0
        return best.move, win_rate


# ---------------------------------------------------------------------------
# Variant 3 — Top-K MCTS (expand K children per iteration)
# ---------------------------------------------------------------------------

class MCTSTopK(MCTS):
    """
    MCTS variant that expands K children simultaneously per iteration.
    Higher K explores more breadth at the cost of depth.
    K=1 is equivalent to standard MCTS.
    """

    name = "MCTS Top-K"

    def __init__(self, k=3, exploration_constant=math.sqrt(2), max_simulations=500, max_time=1.0):
        super().__init__(exploration_constant, max_simulations, max_time)
        self.k = k
        self.name = f"MCTS Top-{k}"

    def search(self, root_state):
        root = MCTSNode(root_state)
        start = time.time()
        sims = 0

        while time.time() - start < self.max_time and sims < self.max_simulations:
            node = root
            while node.has_children() and node.is_fully_expanded():
                node = node.select_child(self.c)

            if not node.state.is_game_over() and node.untried_moves:
                new_children = node.expand_k(self.k)
                for child in new_children:
                    result = child.simulate_random()
                    child.backpropagate(result)
                    sims += 1
            else:
                result = node.simulate_random()
                node.backpropagate(result)
                sims += 1

        if not root.children:
            valid = root_state.get_valid_moves()
            return (random.choice(valid) if valid else None), 0.0

        best = max(root.children, key=lambda ch: ch.visits)
        win_rate = best.wins / best.visits if best.visits > 0 else 0.0
        return best.move, win_rate


# ---------------------------------------------------------------------------
# Utility functions for evaluation
# ---------------------------------------------------------------------------

def run_games(mcts1, mcts2, n_games=20, verbose=False):
    """
    Play n_games between mcts1 (Player 1) and mcts2 (Player 2).

    Returns:
        dict with keys 'p1_wins', 'p2_wins', 'draws', 'p1_win_rate'
    """
    p1_wins = p2_wins = draws = 0

    for g in range(n_games):
        state = PopOutState()
        agents = {PLAYER_1: mcts1, PLAYER_2: mcts2}

        while not state.is_game_over():
            agent = agents[state.get_current_player()]
            move = agent.get_best_move(state)
            if move is None:
                break
            state = state.make_move(move)

        winner = state.get_winner()
        if winner == PLAYER_1:
            p1_wins += 1
        elif winner == PLAYER_2:
            p2_wins += 1
        else:
            draws += 1

        if verbose:
            print(f"  Game {g+1}/{n_games}: winner={winner}")

    total = p1_wins + p2_wins + draws
    return {
        'p1_wins': p1_wins,
        'p2_wins': p2_wins,
        'draws': draws,
        'p1_win_rate': p1_wins / total if total > 0 else 0.0,
    }


def search_convergence(mcts_class, root_state, checkpoints, **kwargs):
    """
    Measure win rate of the chosen move as simulations increase.

    Args:
        mcts_class   : MCTS class to instantiate
        root_state   : PopOutState to analyse
        checkpoints  : list of simulation counts, e.g. [50, 100, 200, 500, 1000]
        **kwargs     : extra args forwarded to mcts_class

    Returns:
        list of (n_sims, win_rate) tuples
    """
    results = []
    for n in checkpoints:
        agent = mcts_class(max_simulations=n, max_time=9999, **kwargs)
        _, wr = agent.search(root_state)
        results.append((n, wr))
    return results


# ---------------------------------------------------------------------------
# Quick self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=== MCTS variants self-test ===\n")
    state = PopOutState()

    for cls, kwargs in [
        (MCTS, {}),
        (MCTSHeuristic, {}),
        (MCTSTopK, {'k': 3}),
    ]:
        agent = cls(max_simulations=200, max_time=2.0, **kwargs)
        move, wr = agent.search(state)
        print(f"{agent.name:30s}  move={move}  win_rate={wr:.3f}")

    print("\nConvergence test (Standard MCTS):")
    pts = search_convergence(MCTS, state, [50, 100, 200, 500])
    for n, wr in pts:
        print(f"  sims={n:4d}  win_rate={wr:.3f}")

    print("\nHead-to-head (10 games, Standard vs Heuristic):")
    a1 = MCTS(max_simulations=100, max_time=0.3)
    a2 = MCTSHeuristic(max_simulations=100, max_time=0.3)
    res = run_games(a1, a2, n_games=10)
    print(f"  P1 wins={res['p1_wins']}  P2 wins={res['p2_wins']}  Draws={res['draws']}")
    print(f"  P1 win rate: {res['p1_win_rate']:.2%}")
