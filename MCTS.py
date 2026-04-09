import math
import random
import copy
import pandas as pd

class MCTSNode:
    def __init__(self, state, parent=None, move=None, max_children=None):
        self.state = state
        self.parent = parent
        self.move = move
        self.children = []
        self.visits = 0
        self.wins = 0
        self.max_children = max_children

    def is_fully_expanded(self):
        return len(self.children) >= len(self.state.get_legal_moves())

    def best_child(self, c_param=1.4):
        choices_weights = []
        for child in self.children:
            if child.visits > 0:
                weight = (child.wins / child.visits) + c_param * math.sqrt(math.log(self.visits) / child.visits)
            else:
                weight = float('inf')
            choices_weights.append(weight)
        return self.children[choices_weights.index(max(choices_weights))]

    def expand(self):
        tried_moves = [child.move for child in self.children]
        legal_moves = self.state.get_legal_moves()
        random.shuffle(legal_moves)
        for move in legal_moves:
            if move not in tried_moves:
                next_state = self.state.clone()
                next_state.make_move(move)
                child_node = MCTSNode(next_state, parent=self, move=move, max_children=self.max_children)
                self.children.append(child_node)
                if self.max_children and len(self.children) >= self.max_children:
                    break
                return child_node
        return None

    def simulate(self):
        current_state = self.state.clone()
        while not current_state.is_terminal():
            legal_moves = current_state.get_legal_moves()
            move = random.choice(legal_moves)
            current_state.make_move(move)
        return current_state.get_winner()

    def backpropagate(self, result):
        node = self
        while node is not None:
            node.visits += 1
            if result == 0:
                pass
            elif result == 3 - node.state.get_current_player():
                node.wins += 1
            node = node.parent


class MCTS:
    def __init__(self, iterations=1000, max_children=14):
        self.iterations = iterations
        self.max_children = max_children

    def search(self, initial_state):
        root = MCTSNode(initial_state, max_children=self.max_children)
        for _ in range(self.iterations):
            node = root
            while not node.state.is_terminal() and node.is_fully_expanded():
                node = node.best_child()
            if not node.state.is_terminal():
                node = node.expand()
            if node:
                result = node.simulate()
                node.backpropagate(result)
        return root.best_child(c_param=0).move
