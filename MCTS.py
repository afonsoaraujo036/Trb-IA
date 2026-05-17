import math
import time
import random
import copy

from PopOut import PopOutState, PLAYER_1, PLAYER_2


# ---------------------------------------------------------------------------
# MCTS Node
# ---------------------------------------------------------------------------

class MCTSNode:

    def __init__(self, state, parent=None, move=None):

        self.state = state
        self.parent = parent
        self.move = move

        self.children = []

        self.visits = 0
        self.wins = 0.0

        self.untried_moves = state.get_valid_moves()

    # -----------------------------------------------------------------------

    def uct_value(self, c):

        if self.visits == 0:
            return float("inf")

        exploitation = self.wins / self.visits

        exploration = c * math.sqrt(
            math.log(self.parent.visits) / self.visits
        )

        return exploitation + exploration

    # -----------------------------------------------------------------------

    def select_child(self, c):

        return max(
            self.children,
            key=lambda ch: ch.uct_value(c)
        )

    # -----------------------------------------------------------------------

    def expand(self):
        """
        Expand using center-priority move ordering.
        """

        if not self.untried_moves:
            return None

        sorted_moves = sorted(
            self.untried_moves,
            key=lambda m: abs(m[1] - 3)
        )

        move = sorted_moves[0]

        self.untried_moves.remove(move)

        child_state = self.state.make_move(move)

        child = MCTSNode(
            child_state,
            parent=self,
            move=move
        )

        self.children.append(child)

        return child

    # -----------------------------------------------------------------------

    def simulate_random(self, max_depth=100):

        state = copy.deepcopy(self.state)

        # The player who chose this node is the OPPONENT of the current player
        # (the parent made a move, changing the turn to the current player)
        cp = self.state.get_current_player()
        player_at_node = PLAYER_2 if cp == PLAYER_1 else PLAYER_1

        depth = 0

        while not state.is_game_over() and depth < max_depth:

            moves = state.get_valid_moves()

            if not moves:
                break

            move = random.choice(moves)

            state = state.make_move(move)

            depth += 1

        return self._result(state, player_at_node)

    # -----------------------------------------------------------------------

    def simulate_heuristic(self, max_depth=100):

        state = copy.deepcopy(self.state)

        # The player who chose this node is the OPPONENT of the current player
        cp = self.state.get_current_player()
        player_at_node = PLAYER_2 if cp == PLAYER_1 else PLAYER_1

        depth = 0

        while not state.is_game_over() and depth < max_depth:

            moves = state.get_valid_moves()

            if not moves:
                break

            chosen = self._heuristic_pick(state, moves)

            state = state.make_move(chosen)

            depth += 1

        return self._result(state, player_at_node)

    # -----------------------------------------------------------------------

    @staticmethod
    def _heuristic_pick(state, moves):

        current = state.get_current_player()

        opponent = state.get_opponent()

        # ---------------------------------------------------------------
        # Immediate win
        # ---------------------------------------------------------------

        for move in moves:

            ns = state.make_move(move)

            if ns.get_winner() == current:
                return move

        # ---------------------------------------------------------------
        # Block opponent immediate win
        # ---------------------------------------------------------------

        safe_moves = []

        for move in moves:

            ns = state.make_move(move)

            opponent_moves = ns.get_valid_moves()

            opponent_can_win = False

            for om in opponent_moves:

                test = ns.make_move(om)

                if test.get_winner() == opponent:
                    opponent_can_win = True
                    break

            if not opponent_can_win:
                safe_moves.append(move)

        if safe_moves:

            safe_moves = sorted(
                safe_moves,
                key=lambda m: abs(m[1] - 3)
            )

            return safe_moves[0]

        # ---------------------------------------------------------------
        # Center preference
        # ---------------------------------------------------------------

        center_sorted = sorted(
            moves,
            key=lambda m: abs(m[1] - 3)
        )

        return random.choice(center_sorted[:3])

    # -----------------------------------------------------------------------

    @staticmethod
    def _result(end_state, player_at_node):
        # get_winner() returns: 0 (ongoing), 1/2 (winner), -1 (draw)
        # It NEVER returns None — the previous check was dead code.
        winner = end_state.get_winner()

        if winner == player_at_node:
            return 1.0

        elif winner == -1:  # Draw: small positive score to prefer draw over loss
            return 0.1

        return 0.0

    # -----------------------------------------------------------------------

    def backpropagate(self, result):

        self.visits += 1

        self.wins += result

        if self.parent:
            self.parent.backpropagate(1.0 - result)

    # -----------------------------------------------------------------------

    def is_fully_expanded(self):

        return len(self.untried_moves) == 0

    # -----------------------------------------------------------------------

    def has_children(self):

        return len(self.children) > 0


# ---------------------------------------------------------------------------
# Base MCTS
# ---------------------------------------------------------------------------

class MCTS:

    name = "Standard MCTS"

    def __init__(
        self,
        exploration_constant=1.2,
        max_simulations=5000,
        max_time=5.0
    ):

        self.c = exploration_constant

        self.max_simulations = max_simulations

        self.max_time = max_time

    # -----------------------------------------------------------------------

    def find_immediate_tactical_move(self, state):

        current = state.get_current_player()

        opponent = state.get_opponent()

        moves = state.get_valid_moves()

        # ---------------------------------------------------------------
        # Winning move
        # ---------------------------------------------------------------

        for move in moves:

            ns = state.make_move(move)

            if ns.get_winner() == current:
                return move

        # ---------------------------------------------------------------
        # Blocking move
        # ---------------------------------------------------------------

        safe_moves = []

        for move in moves:

            ns = state.make_move(move)

            opponent_moves = ns.get_valid_moves()

            opponent_can_win = False

            for om in opponent_moves:

                test = ns.make_move(om)

                if test.get_winner() == opponent:
                    opponent_can_win = True
                    break

            if not opponent_can_win:
                safe_moves.append(move)

        if safe_moves:

            safe_moves = sorted(
                safe_moves,
                key=lambda m: abs(m[1] - 3)
            )

            return safe_moves[0]

        return None

    # -----------------------------------------------------------------------

    def search(self, root_state):

        # ---------------------------------------------------------------
        # Tactical pre-check
        # ---------------------------------------------------------------

        tactical = self.find_immediate_tactical_move(root_state)

        if tactical is not None:
            return tactical, 1.0

        # ---------------------------------------------------------------

        root = MCTSNode(root_state)

        start = time.time()

        sims = 0

        while (
            time.time() - start < self.max_time
            and sims < self.max_simulations
        ):

            node = root

            # -----------------------------------------------------------
            # Selection
            # -----------------------------------------------------------

            while node.has_children() and node.is_fully_expanded():

                node = node.select_child(self.c)

            # -----------------------------------------------------------
            # Expansion
            # -----------------------------------------------------------

            if (
                not node.state.is_game_over()
                and node.untried_moves
            ):

                node = node.expand()

                if node is None:
                    continue

            # -----------------------------------------------------------
            # Simulation
            # -----------------------------------------------------------

            result = node.simulate_random()

            # -----------------------------------------------------------
            # Backpropagation
            # -----------------------------------------------------------

            node.backpropagate(result)

            sims += 1

        # ---------------------------------------------------------------
        # Fallback
        # ---------------------------------------------------------------

        if not root.children:

            valid = root_state.get_valid_moves()

            if not valid:
                return None, 0.0

            return random.choice(valid), 0.0

        # ---------------------------------------------------------------
        # Best child by win rate
        # ---------------------------------------------------------------

        best = max(
            root.children,
            key=lambda ch: (
                ch.wins / ch.visits
                if ch.visits > 0
                else -1
            )
        )

        win_rate = (
            best.wins / best.visits
            if best.visits > 0
            else 0.0
        )

        return best.move, win_rate

    # -----------------------------------------------------------------------

    def get_best_move(self, state):

        move, _ = self.search(state)

        return move


# ---------------------------------------------------------------------------
# Heuristic MCTS (BEST VERSION)
# ---------------------------------------------------------------------------

class MCTSHeuristic(MCTS):

    name = "MCTS + Heuristic Rollout"

    def search(self, root_state):

        # ---------------------------------------------------------------
        # Tactical pre-check
        # ---------------------------------------------------------------

        tactical = self.find_immediate_tactical_move(root_state)

        if tactical is not None:
            return tactical, 1.0

        # ---------------------------------------------------------------

        root = MCTSNode(root_state)

        start = time.time()

        sims = 0

        while (
            time.time() - start < self.max_time
            and sims < self.max_simulations
        ):

            node = root

            # -----------------------------------------------------------
            # Selection
            # -----------------------------------------------------------

            while node.has_children() and node.is_fully_expanded():

                node = node.select_child(self.c)

            # -----------------------------------------------------------
            # Expansion
            # -----------------------------------------------------------

            if (
                not node.state.is_game_over()
                and node.untried_moves
            ):

                node = node.expand()

                if node is None:
                    continue

            # -----------------------------------------------------------
            # Heuristic rollout
            # -----------------------------------------------------------

            result = node.simulate_heuristic()

            # -----------------------------------------------------------
            # Backpropagation
            # -----------------------------------------------------------

            node.backpropagate(result)

            sims += 1

        # ---------------------------------------------------------------
        # Fallback
        # ---------------------------------------------------------------

        if not root.children:

            valid = root_state.get_valid_moves()

            if not valid:
                return None, 0.0

            return random.choice(valid), 0.0

        # ---------------------------------------------------------------
        # Best child by win rate
        # ---------------------------------------------------------------

        best = max(
            root.children,
            key=lambda ch: (
                ch.wins / ch.visits
                if ch.visits > 0
                else -1
            )
        )

        win_rate = (
            best.wins / best.visits
            if best.visits > 0
            else 0.0
        )

        return best.move, win_rate


# ---------------------------------------------------------------------------
# Top-K MCTS — expands k children per iteration (wider exploration)
# ---------------------------------------------------------------------------

class MCTSTopK(MCTS):

    name = "MCTS Top-K"

    def __init__(self, k=3, exploration_constant=1.2, max_simulations=5000, max_time=5.0):

        super().__init__(exploration_constant, max_simulations, max_time)

        self.k = k

    # -----------------------------------------------------------------------

    def search(self, root_state):

        # ---------------------------------------------------------------
        # Tactical pre-check
        # ---------------------------------------------------------------

        tactical = self.find_immediate_tactical_move(root_state)

        if tactical is not None:
            return tactical, 1.0

        # ---------------------------------------------------------------

        root = MCTSNode(root_state)

        start = time.time()

        sims = 0

        while (
            time.time() - start < self.max_time
            and sims < self.max_simulations
        ):

            node = root

            # -----------------------------------------------------------
            # Selection
            # -----------------------------------------------------------

            while node.has_children() and node.is_fully_expanded():

                node = node.select_child(self.c)

            # -----------------------------------------------------------
            # Expand up to k children and simulate each
            # -----------------------------------------------------------

            expanded = 0

            while (
                expanded < self.k
                and not node.state.is_game_over()
                and node.untried_moves
            ):

                child = node.expand()

                if child is None:
                    break

                result = child.simulate_random()

                child.backpropagate(result)

                sims += 1

                expanded += 1

            # If terminal node, still simulate from it
            if expanded == 0:

                result = node.simulate_random()

                node.backpropagate(result)

                sims += 1

        # ---------------------------------------------------------------
        # Fallback
        # ---------------------------------------------------------------

        if not root.children:

            valid = root_state.get_valid_moves()

            if not valid:
                return None, 0.0

            return random.choice(valid), 0.0

        # ---------------------------------------------------------------
        # Best child by win rate
        # ---------------------------------------------------------------

        best = max(
            root.children,
            key=lambda ch: (
                ch.wins / ch.visits
                if ch.visits > 0
                else -1
            )
        )

        win_rate = (
            best.wins / best.visits
            if best.visits > 0
            else 0.0
        )

        return best.move, win_rate


# ---------------------------------------------------------------------------
# Evaluation utilities
# ---------------------------------------------------------------------------

def run_games(mcts1, mcts2, n_games=20, verbose=False):

    p1_wins = 0
    p2_wins = 0
    draws = 0

    for g in range(n_games):

        state = PopOutState()

        agents = {
            PLAYER_1: mcts1,
            PLAYER_2: mcts2
        }

        while not state.is_game_over():

            current = state.get_current_player()

            agent = agents[current]

            move = agent.get_best_move(state)

            if move is None:
                break

            state = state.make_move(move)

        winner = state.get_winner()

        if winner == PLAYER_1:
            p1_wins += 1

        elif winner == PLAYER_2:
            p2_wins += 1

        elif winner == -1:  # draw by repetition or board full
            draws += 1
        # winner == 0 means move was None and game loop exited early (should not happen)

        if verbose:
            print(f"Game {g+1}/{n_games} -> Winner: {winner}")

    total = p1_wins + p2_wins + draws

    return {
        "p1_wins": p1_wins,
        "p2_wins": p2_wins,
        "draws": draws,
        "p1_win_rate":
            p1_wins / total if total > 0 else 0.0
    }


# ---------------------------------------------------------------------------

def search_convergence(
    mcts_class,
    root_state,
    checkpoints,
    **kwargs
):

    results = []

    for n in checkpoints:

        agent = mcts_class(
            max_simulations=n,
            max_time=9999,
            **kwargs
        )

        _, wr = agent.search(root_state)

        results.append((n, wr))

    return results


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":

    print("\n=== STRONG MCTS TEST ===\n")

    state = PopOutState()

    standard = MCTS(
        max_simulations=1000,
        max_time=2.0
    )

    heuristic = MCTSHeuristic(
        max_simulations=5000,
        max_time=5.0
    )

    move1, wr1 = standard.search(state)

    print(f"{standard.name}")
    print(f"Move: {move1}")
    print(f"Win rate: {wr1:.3f}\n")

    move2, wr2 = heuristic.search(state)

    print(f"{heuristic.name}")
    print(f"Move: {move2}")
    print(f"Win rate: {wr2:.3f}\n")

    print("Running matches...\n")

    results = run_games(
        standard,
        heuristic,
        n_games=10,
        verbose=True
    )

    print("\nResults:")
    print(results)
