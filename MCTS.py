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
        legal = self.state.get_legal_moves()
        limit = min(len(legal), self.max_children) if self.max_children else len(legal)
        return len(self.children) >= limit

    def best_child(self, c_param=1.4):
        best, best_w = None, -float('inf')
        for child in self.children:
            if child.visits == 0:
                return child
            w = (child.wins / child.visits) + c_param * math.sqrt(
                math.log(self.visits) / child.visits
            )
            if w > best_w:
                best_w = w
                best = child
        return best

    def expand(self):
        tried = {child.move for child in self.children}
        legal = self.state.get_legal_moves()
        random.shuffle(legal)
        for move in legal:
            if move not in tried:
                next_state = self.state.clone()
                next_state.make_move(move)
                child = MCTSNode(next_state, parent=self, move=move,
                                 max_children=self.max_children)
                self.children.append(child)
                return child
        return None

    def simulate(self):
        current = self.state.clone()
        depth = 0
        while not current.is_terminal() and depth < 60:
            moves = current.get_legal_moves()
            current.make_move(random.choice(moves))
            depth += 1
        return current.get_winner()

    def backpropagate(self, result):
        node = self
        while node is not None:
            node.visits += 1
            if result is not None and result != 0:
                if result == 3 - node.state.current_player:
                    node.wins += 1
            node = node.parent


class MCTS:
    def __init__(self, level=3):
        cfg = MCTS_LEVELS.get(level, MCTS_LEVELS[3])
        self.iterations   = cfg['iterations']
        self.max_children = cfg['max_children']
        self.c_param      = cfg['c_param']
        self.level        = level

    def search(self, state):
        root = MCTSNode(state.clone(), max_children=self.max_children)
        for _ in range(self.iterations):
            node = root
            while not node.state.is_terminal() and node.is_fully_expanded():
                node = node.best_child(self.c_param)
            if not node.state.is_terminal():
                expanded = node.expand()
                if expanded:
                    node = expanded
            result = node.simulate()
            node.backpropagate(result)
        best = root.best_child(c_param=0)
        return best.move if best else random.choice(state.get_legal_moves())
