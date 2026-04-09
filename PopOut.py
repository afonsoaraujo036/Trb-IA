import copy

ROWS = 6
COLS = 7

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
