import math
import random
import copy

ROWS = 6
COLS = 7

MCTS_LEVELS = {
    1: {'iterations': 50,   'max_children': 3,  'c_param': 2.5},
    2: {'iterations': 500,  'max_children': 14, 'c_param': 0.7},
    3: {'iterations': 2000, 'max_children': 14, 'c_param': 1.4},
}


class GameState:
    def __init__(self):
        self.board = [[0 for _ in range(COLS)] for _ in range(ROWS)]
        self.current_player = 1
        self.history = []

    def _board_key(self):
        return (tuple(tuple(r) for r in self.board), self.current_player)

    def _gravity(self, col):
        for row in range(ROWS - 1, 0, -1):
            if self.board[row][col] == 0:
                for above in range(row - 1, -1, -1):
                    if self.board[above][col] != 0:
                        self.board[row][col] = self.board[above][col]
                        self.board[above][col] = 0
                        row = above
                break

    def get_legal_moves(self):
        moves = []
        for col in range(COLS):
            if self.board[0][col] == 0:
                moves.append(('drop', col))
        for col in range(COLS):
            if self.board[ROWS - 1][col] == self.current_player:
                moves.append(('pop', col))
        return moves

    def make_move(self, move):
        kind, col = move
        if kind == 'drop':
            return self._drop(col)
        elif kind == 'pop':
            return self._pop(col)
        return False

    def _drop(self, col):
        if col < 0 or col >= COLS or self.board[0][col] != 0:
            return False
        for row in reversed(range(ROWS)):
            if self.board[row][col] == 0:
                self.board[row][col] = self.current_player
                break
        self._record_and_switch()
        return True

    def _pop(self, col):
        if col < 0 or col >= COLS:
            return False
        if self.board[ROWS - 1][col] != self.current_player:
            return False
        self.board[ROWS - 1][col] = 0
        self._gravity(col)
        self._record_and_switch()
        return True

    def _record_and_switch(self):
        self.history.append(self._board_key())
        self.current_player = 3 - self.current_player

    def is_terminal(self):
        return self.get_winner() is not None

    def _is_draw(self):
        return (all(self.board[0][col] != 0 for col in range(COLS)) and
                not self._find_four_in_rows(1) and
                not self._find_four_in_rows(2))

    def _is_repetition_draw(self):
        key = self._board_key()
        return self.history.count(key) >= 3

    def _find_four_in_rows(self, player):
        for row in range(ROWS):
            for col in range(COLS):
                if self.board[row][col] != player:
                    continue
                for dr, dc in [(0, 1), (1, 0), (1, 1), (1, -1)]:
                    if all(
                        0 <= row + i * dr < ROWS and
                        0 <= col + i * dc < COLS and
                        self.board[row + i * dr][col + i * dc] == player
                        for i in range(4)
                    ):
                        return True
        return False

    def get_winner(self):
        p1 = self._find_four_in_rows(1)
        p2 = self._find_four_in_rows(2)
        if p1 and p2:
            return 3 - self.current_player
        if p1:
            return 1
        if p2:
            return 2
        if self._is_draw() or self._is_repetition_draw():
            return 0
        return None

    def clone(self):
        new = GameState()
        new.board = copy.deepcopy(self.board)
        new.current_player = self.current_player
        new.history = self.history[:]
        return new

    def print_board(self):
        symbols = {0: '.', 1: 'X', 2: 'O'}
        print(' '.join(str(c) for c in range(COLS)))
        print('-' * (COLS * 2 - 1))
        for row in self.board:
            print(' '.join(symbols[cell] for cell in row))
        print('-' * (COLS * 2 - 1))
        pop_cols = {col for col in range(COLS)
                    if self.board[ROWS - 1][col] == self.current_player}
        if pop_cols:
            print(' '.join('↑' if col in pop_cols else ' ' for col in range(COLS)))
        print()


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


def get_human_move(game: GameState):
    legal = game.get_legal_moves()
    symbol = 'X' if game.current_player == 1 else 'O'
    print(f"Jogador {symbol}, escolhe o teu movimento.")
    print("  drop <col>  – coloca um disco (ex: drop 3)")
    print("  pop  <col>  – retira da base  (ex: pop 2)")
    while True:
        raw = input("Movimento: ").strip().lower()
        parts = raw.split()
        if len(parts) != 2:
            print("Formato inválido. Usa: drop <col> ou pop <col>")
            continue
        kind, col_str = parts
        if kind not in ('drop', 'pop'):
            print("Tipo inválido. Usa 'drop' ou 'pop'.")
            continue
        try:
            col = int(col_str)
        except ValueError:
            print("Coluna inválida.")
            continue
        move = (kind, col)
        if move not in legal:
            print(f"Movimento ilegal. Movimentos legais: {legal}")
            continue
        return move


def get_level(player_label):
    while True:
        raw = input(f"Nível do computador {player_label} (1=fácil / 2=médio / 3=difícil): ").strip()
        if raw in ('1', '2', '3'):
            return int(raw)
        print("Escolhe 1, 2 ou 3.")


def play_game():
    print("=== PopOut ===")
    print("1 – Humano vs Humano")
    print("2 – Humano vs Computador")
    print("3 – Computador vs Computador")
    mode = input("Modo: ").strip()

    game = GameState()

    mcts1 = mcts2 = None
    if mode == '2':
        mcts2 = MCTS(level=get_level("(jogador O)"))
    elif mode == '3':
        mcts1 = MCTS(level=get_level("(jogador X)"))
        mcts2 = MCTS(level=get_level("(jogador O)"))

    game.print_board()

    while not game.is_terminal():
        symbol = 'X' if game.current_player == 1 else 'O'

        if mode == '1':
            move = get_human_move(game)

        elif mode == '2':
            if game.current_player == 1:
                move = get_human_move(game)
            else:
                print("Computador (O) está a pensar...")
                move = mcts2.search(game)
                print(f"Computador joga: {move[0]} coluna {move[1]}")

        elif mode == '3':
            mcts = mcts1 if game.current_player == 1 else mcts2
            print(f"Computador ({symbol}) está a pensar...")
            move = mcts.search(game)
            print(f"Computador ({symbol}) joga: {move[0]} coluna {move[1]}")

        else:
            print("Modo inválido.")
            return

        if not game.make_move(move):
            print("Movimento inválido, tenta novamente.")
            continue

        game.print_board()

    result = game.get_winner()
    if result == 0:
        print("Empate!")
    elif result == 1:
        print("Jogador X venceu!")
    else:
        print("Jogador O venceu!")


if __name__ == "__main__":
    play_game()
