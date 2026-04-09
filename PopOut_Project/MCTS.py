"""
Monte Carlo Tree Search (MCTS) Implementation for PopOut

Adapted from Connect Four MCTS implementation
Uses UCT (Upper Confidence Bound for Trees) formula for node selection
"""

import math
import time
import random
import copy
from PopOut import PopOutState, PLAYER_1, PLAYER_2


class MCTSNode:
    """
    Node in the MCTS tree for PopOut game
    """

    def __init__(self, state, parent=None, move=None):
        """
        Initialize MCTS node

        Args:
            state: PopOutState object
            parent: parent MCTSNode
            move: move that led to this state (tuple: ('drop', col) or ('pop', col))
        """
        self.state = state
        self.parent = parent
        self.move = move
        self.children = []
        self.visits = 0
        self.wins = 0  # Number of wins for the player who made the move that led to this node
        self.untried_moves = state.get_valid_moves()

    def uct_value(self, exploration_constant=math.sqrt(2)):
        """
        Calculate Upper Confidence Bound for Trees (UCT) value

        Args:
            exploration_constant: C parameter in UCT formula

        Returns:
            UCT value for node selection
        """
        if self.visits == 0:
            return float('inf')

        exploitation = self.wins / self.visits
        exploration = exploration_constant * math.sqrt(math.log(self.parent.visits) / self.visits)

        return exploitation + exploration

    def select_child(self, exploration_constant=math.sqrt(2)):
        """
        Select the child with highest UCT value

        Returns:
            Best child node according to UCT
        """
        if not self.children:
            return None

        return max(self.children, key=lambda child: child.uct_value(exploration_constant))

    def expand(self):
        """
        Expand node by creating one new child

        Returns:
            New child node, or None if no moves available
        """
        if not self.untried_moves:
            return None

        # Select random untried move
        move = random.choice(self.untried_moves)
        self.untried_moves.remove(move)

        # Create new state after the move
        new_state = self.state.make_move(move)

        # Create child node
        child = MCTSNode(new_state, parent=self, move=move)
        self.children.append(child)

        return child

    def simulate(self, max_depth=50):
        """
        Run random simulation from current node

        Args:
            max_depth: Maximum simulation depth

        Returns:
            1.0 if current player wins, 0.0 if opponent wins, 0.5 for draw
        """
        current_state = copy.deepcopy(self.state)
        depth = 0

        while not current_state.is_game_over() and depth < max_depth:
            valid_moves = current_state.get_valid_moves()

            if not valid_moves:
                # No moves available - this shouldn't happen in normal play
                return 0.5

            # Choose random move
            move = random.choice(valid_moves)
            current_state = current_state.make_move(move)
            depth += 1

        # Check final result
        winner = current_state.get_winner()
        if winner == self.state.get_current_player():
            return 1.0  # Current player (who made the move) wins
        elif winner == self.state.get_opponent():
            return 0.0  # Opponent wins
        else:
            return 0.5  # Draw

    def backpropagate(self, result):
        """
        Backpropagate simulation result up the tree

        Args:
            result: Simulation result (1.0, 0.0, or 0.5)
        """
        self.visits += 1
        self.wins += result

        if self.parent:
            # For parent, invert the result (opponent's perspective)
            self.parent.backpropagate(1.0 - result)

    def is_fully_expanded(self):
        """Check if node is fully expanded"""
        return len(self.untried_moves) == 0

    def has_children(self):
        """Check if node has children"""
        return len(self.children) > 0


class MCTS:
    """
    Monte Carlo Tree Search algorithm for PopOut
    """

    def __init__(self, exploration_constant=math.sqrt(2), max_simulations=1000, max_time=1.0):
        """
        Initialize MCTS

        Args:
            exploration_constant: C parameter for UCT
            max_simulations: Maximum number of simulations per search
            max_time: Maximum search time in seconds
        """
        self.exploration_constant = exploration_constant
        self.max_simulations = max_simulations
        self.max_time = max_time

    def search(self, root_state):
        """
        Run MCTS search from given state

        Args:
            root_state: PopOutState to search from

        Returns:
            tuple: (best_move, win_rate) where win_rate is wins/visits for best move
        """
        root = MCTSNode(root_state)

        start_time = time.time()
        simulations = 0

        while (time.time() - start_time < self.max_time and
               simulations < self.max_simulations):

            # Selection: traverse tree to leaf node
            node = root
            while node.has_children() and node.is_fully_expanded():
                node = node.select_child(self.exploration_constant)

            # Expansion: add new child if possible
            if not node.state.is_game_over() and node.untried_moves:
                node = node.expand()
                if not node:
                    continue

            # Simulation: random playout
            result = node.simulate()

            # Backpropagation: update statistics up the tree
            node.backpropagate(result)

            simulations += 1

        # Return best move based on visit count
        if not root.children:
            # No children - return random valid move
            valid_moves = root_state.get_valid_moves()
            return random.choice(valid_moves) if valid_moves else None, 0.0

        # Find child with most visits
        best_child = max(root.children, key=lambda child: child.visits)
        win_rate = best_child.wins / best_child.visits if best_child.visits > 0 else 0.0

        return best_child.move, win_rate

    def get_best_move(self, state, **kwargs):
        """
        Convenience method to get best move for a state

        Args:
            state: PopOutState
            **kwargs: Override default parameters

        Returns:
            Best move tuple ('drop', col) or ('pop', col)
        """
        # Override parameters if provided
        exploration_constant = kwargs.get('exploration_constant', self.exploration_constant)
        max_simulations = kwargs.get('max_simulations', self.max_simulations)
        max_time = kwargs.get('max_time', self.max_time)

        # Create temporary MCTS with new parameters
        temp_mcts = MCTS(exploration_constant, max_simulations, max_time)
        move, win_rate = temp_mcts.search(state)

        return move


# Test MCTS implementation
if __name__ == "__main__":
    print("Testing MCTS implementation...")

    # Create initial state
    state = PopOutState()

    # Create MCTS instance
    mcts = MCTS(max_simulations=100, max_time=0.5)

    # Get best move
    print("Getting best move for initial state...")
    best_move, win_rate = mcts.search(state)

    print(f"Best move: {best_move}")
    print(f"Win rate: {win_rate:.3f}")

    # Test with a more developed position
    print("\nTesting with developed position...")

    # Make some moves to create a more interesting position
    test_state = state
    moves = [('drop', 3), ('drop', 3), ('drop', 2), ('drop', 2), ('drop', 1)]
    for move in moves:
        if move in test_state.get_valid_moves():
            test_state = test_state.make_move(move)

    print("Test position:")
    test_state.display_board()

    best_move2, win_rate2 = mcts.search(test_state)
    print(f"Best move: {best_move2}")
    print(f"Win rate: {win_rate2:.3f}")

    print("\nMCTS implementation test completed!")