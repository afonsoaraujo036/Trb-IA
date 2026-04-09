"""
PopOut Game Implementation

Regras do PopOut:
- O tabuleiro começa vazio e os jogadores alternam turnos
- Em cada turno, o jogador escolhe uma de duas ações:
  * drop: colocar uma peça sua numa coluna não cheia
  * pop: remover uma peça sua da base de uma coluna, fazendo descer todas as peças acima
- Ganha quem formar primeiro uma sequência de 4 peças consecutivas na horizontal, vertical ou diagonal
- Se uma jogada pop criar quatro-em-linha para ambos os jogadores, ganha o jogador que fez o pop
- Se o tabuleiro estiver cheio, o jogador da vez pode optar por fazer um pop válido ou terminar o jogo em empate
- Se o mesmo estado se repetir três vezes, o jogo pode ser declarado empate
"""

import math
import time
import os
import random
import copy
from os import system
import sys
import csv

# Define constants
ROWS = 6
COLS = 7
WIN_LENGTH = 4
EMPTY = 0
PLAYER_1 = 1
PLAYER_2 = 2

# Define CSV file for dataset generation
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR   = os.path.join(SCRIPT_DIR, 'data')
CSV_FILE   = os.path.join(DATA_DIR, 'popout_pairs.csv')

os.makedirs(DATA_DIR, exist_ok=True)

# Create CSV file if it doesn't exist
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        # Header: 42 board positions + move_type + move_col
        header = [f'c{i}' for i in range(ROWS * COLS)] + ['move_type', 'move_col']
        writer.writerow(header)


class PopOutState:
    """
    Represents the state of a PopOut game
    """

    def __init__(self, board=None, current_player=PLAYER_1, last_move=None, last_move_type=None, state_history=None):
        """
        Initialize PopOut game state

        Args:
            board: 6x7 board (list of lists), None for empty board
            current_player: PLAYER_1 or PLAYER_2
            last_move: column of last move (0-6)
            last_move_type: 'drop' or 'pop'
            state_history: dict mapping state_key -> count (for repetition detection)
        """
        if board is None:
            self.board = [[EMPTY] * COLS for _ in range(ROWS)]
        else:
            # Deep copy to avoid reference issues
            self.board = [row[:] for row in board]

        self.current_player = current_player
        self.last_move = last_move
        self.last_move_type = last_move_type
        self.state_history = dict(state_history) if state_history is not None else {}  # For repetition detection

    def get_current_player(self):
        """Return the current player"""
        return self.current_player

    def get_opponent(self):
        """Return the opponent player"""
        return PLAYER_2 if self.current_player == PLAYER_1 else PLAYER_1

    def get_valid_moves(self):
        """
        Return all valid moves for current player
        Returns list of tuples: ('drop', col) or ('pop', col)
        """
        moves = []

        # Drop moves: columns that are not full
        for col in range(COLS):
            if self.board[0][col] == EMPTY:  # Top row is empty
                moves.append(('drop', col))

        # Pop moves: columns where bottom piece belongs to current player
        for col in range(COLS):
            if self.board[ROWS-1][col] == self.current_player:
                moves.append(('pop', col))

        return moves

    def make_move(self, move):
        """
        Apply a move to create a new state

        Args:
            move: tuple ('drop', col) or ('pop', col)

        Returns:
            new PopOutState after the move
        """
        move_type, col = move
        new_board = [row[:] for row in self.board]

        if move_type == 'drop':
            # Find the lowest empty position in the column
            for row in range(ROWS-1, -1, -1):
                if new_board[row][col] == EMPTY:
                    new_board[row][col] = self.current_player
                    break
        elif move_type == 'pop':
            # Remove bottom piece (must belong to current player)
            if new_board[ROWS-1][col] == self.current_player:
                # Remove bottom piece
                new_board[ROWS-1][col] = EMPTY
                # Shift all pieces above down by one
                for row in range(ROWS-1, 0, -1):
                    new_board[row][col] = new_board[row-1][col]
                new_board[0][col] = EMPTY

        # Switch to next player
        next_player = self.get_opponent()

        # Create new state, propagating the state history
        new_state = PopOutState(new_board, next_player, col, move_type, state_history=self.state_history)
        # Record the new position in the history
        state_key = new_state.get_state_key()
        new_state.state_history[state_key] = new_state.state_history.get(state_key, 0) + 1
        return new_state

    def is_board_full(self):
        """Check if the board is completely full"""
        return all(cell != EMPTY for row in self.board for cell in row)

    def check_four_in_row(self, player):
        """
        Check if player has four in a row (horizontal, vertical, diagonal)

        Args:
            player: PLAYER_1 or PLAYER_2

        Returns:
            True if player has four in a row
        """
        # Check horizontal
        for row in range(ROWS):
            for col in range(COLS - WIN_LENGTH + 1):
                if all(self.board[row][col + i] == player for i in range(WIN_LENGTH)):
                    return True

        # Check vertical
        for col in range(COLS):
            for row in range(ROWS - WIN_LENGTH + 1):
                if all(self.board[row + i][col] == player for i in range(WIN_LENGTH)):
                    return True

        # Check diagonal (top-left to bottom-right)
        for row in range(ROWS - WIN_LENGTH + 1):
            for col in range(COLS - WIN_LENGTH + 1):
                if all(self.board[row + i][col + i] == player for i in range(WIN_LENGTH)):
                    return True

        # Check diagonal (top-right to bottom-left)
        for row in range(ROWS - WIN_LENGTH + 1):
            for col in range(WIN_LENGTH - 1, COLS):
                if all(self.board[row + i][col - i] == player for i in range(WIN_LENGTH)):
                    return True

        return False

    def check_winner(self):
        """
        Check for winner considering PopOut special rules

        Returns:
            0: game continues
            1: player 1 wins
            2: player 2 wins
            -1: draw
        """
        current_player = self.get_opponent()  # The player who just moved
        opponent = self.current_player           # The player who moves next

        current_has_win = self.check_four_in_row(current_player)
        opponent_has_win = self.check_four_in_row(opponent)

        # Rule 1: Simultaneous four-in-rows after pop -> pop-maker wins
        if self.last_move_type == 'pop' and current_has_win and opponent_has_win:
            return current_player

        # Normal win: the player who just moved has 4-in-a-row
        if current_has_win:
            return current_player

        # A pop can cascade pieces and accidentally give the opponent 4-in-a-row
        if opponent_has_win:
            return opponent

        # Rule 2: Board full - if no valid moves remain, it is a draw
        if self.is_board_full():
            valid_moves = self.get_valid_moves()
            if not valid_moves:  # No drop or pop moves available
                return -1  # Draw
            # If pop moves are available the game continues

        # Rule 3: Triple repetition (read-only; history is updated in make_move)
        state_key = self.get_state_key()
        if self.state_history.get(state_key, 0) >= 3:
            return -1  # Draw due to repetition

        return 0  # Game continues

    def get_state_key(self):
        """Get a hashable representation of the current state"""
        board_tuple = tuple(tuple(row) for row in self.board)
        return (board_tuple, self.current_player)

    def is_game_over(self):
        """Check if the game has ended"""
        return self.check_winner() != 0

    def get_winner(self):
        """Get the winner (0 for ongoing, 1/2 for players, -1 for draw)"""
        return self.check_winner()

    def display_board(self):
        """Display the current board state"""
        print("\nCurrent board:")
        print("-" * (COLS * 2 + 1))
        for row in self.board:
            row_str = "|"
            for cell in row:
                if cell == EMPTY:
                    row_str += " |"
                elif cell == PLAYER_1:
                    row_str += "X|"
                else:  # PLAYER_2
                    row_str += "O|"
            print(row_str)
        print("-" * (COLS * 2 + 1))

        if self.current_player == PLAYER_1:
            print("Current player: X")
        else:
            print("Current player: O")

        valid_moves = self.get_valid_moves()
        if valid_moves:
            print(f"Valid moves: {valid_moves}")
        else:
            print("No valid moves available")

    def get_board_flat(self):
        """Get flattened board representation for dataset"""
        return [cell for row in self.board for cell in row]


# Test the implementation
if __name__ == "__main__":
    print("Testing PopOut implementation...")

    # Create initial state
    state = PopOutState()

    # Test some moves
    print("Initial state:")
    state.display_board()

    # Make a drop move
    if ('drop', 3) in state.get_valid_moves():
        state = state.make_move(('drop', 3))
        print("\nAfter drop in column 3:")
        state.display_board()

    # Make another drop
    if ('drop', 3) in state.get_valid_moves():
        state = state.make_move(('drop', 3))
        print("\nAfter second drop in column 3:")
        state.display_board()

    # Test pop move
    if ('pop', 3) in state.get_valid_moves():
        state = state.make_move(('pop', 3))
        print("\nAfter pop in column 3:")
        state.display_board()

    # Test win condition - create a horizontal win
    print("\n" + "="*50)
    print("Testing win conditions...")

    # Create a board with horizontal win for player 1
    win_board = [
        [0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0],
        [1, 1, 1, 1, 0, 0, 0]  # Four X's in a row
    ]
    win_state = PopOutState(win_board, PLAYER_2, last_move=3, last_move_type='drop')
    print(f"Horizontal win test - Winner: {win_state.get_winner()}")

    # Test vertical win
    v_win_board = [
        [0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0],
        [1, 0, 0, 0, 0, 0, 0],
        [1, 0, 0, 0, 0, 0, 0],
        [1, 0, 0, 0, 0, 0, 0],
        [1, 0, 0, 0, 0, 0, 0]
    ]
    v_win_state = PopOutState(v_win_board, PLAYER_2, last_move=0, last_move_type='drop')
    print(f"Vertical win test - Winner: {v_win_state.get_winner()}")

    # Test diagonal win
    d_win_board = [
        [0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 1, 0, 0, 0],
        [0, 0, 1, 0, 0, 0, 0],
        [0, 1, 0, 0, 0, 0, 0],
        [1, 0, 0, 0, 0, 0, 0]
    ]
    d_win_state = PopOutState(d_win_board, PLAYER_2, last_move=0, last_move_type='drop')
    print(f"Diagonal win test - Winner: {d_win_state.get_winner()}")

    # Test pop cascading -> opponent gets 4-in-a-row (opponent should win)
    print("\n" + "="*50)
    print("Testing special PopOut rules...")

    # After X pops a column, the cascade gives O (PLAYER_2) a horizontal 4-in-a-row
    # X (PLAYER_1) has no 4-in-a-row -> O wins
    pop_cascade_board = [
        [0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0],
        [2, 2, 2, 2, 0, 0, 0],
    ]
    pop_cascade_state = PopOutState(pop_cascade_board, PLAYER_2, last_move=3, last_move_type='pop')
    result = pop_cascade_state.get_winner()
    print(f"Pop cascade -> opponent wins test - Winner: {result} (expected: 2)")
    assert result == 2, f"FAIL: expected 2, got {result}"

    # Test simultaneous 4-in-a-row after pop -> pop-maker (PLAYER_1 = X) wins
    simultaneous_board = [
        [0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0],
        [1, 0, 0, 0, 0, 0, 0],
        [1, 0, 0, 0, 0, 0, 0],
        [1, 0, 0, 0, 0, 0, 0],
        [1, 2, 2, 2, 2, 0, 0],
    ]
    simul_state = PopOutState(simultaneous_board, PLAYER_2, last_move=0, last_move_type='pop')
    result = simul_state.get_winner()
    print(f"Simultaneous pop rule test - Winner: {result} (expected: 1 / pop-maker)")
    assert result == 1, f"FAIL: expected 1, got {result}"

    # Test triple repetition rule (P1 drops col 0, P2 drops col 1, P1 pops col 0, P2 pops col 1 - cycle)
    rep_state = PopOutState()
    rep_triggered = False
    for cycle in range(4):
        rep_state = rep_state.make_move(('drop', 0))   # P1 drops col 0
        if rep_state.get_winner() != 0:
            rep_triggered = True; break
        rep_state = rep_state.make_move(('drop', 1))   # P2 drops col 1
        if rep_state.get_winner() != 0:
            rep_triggered = True; break
        rep_state = rep_state.make_move(('pop', 0))    # P1 pops own piece at col 0
        if rep_state.get_winner() != 0:
            rep_triggered = True; break
        rep_state = rep_state.make_move(('pop', 1))    # P2 pops own piece at col 1
        if rep_state.get_winner() != 0:
            rep_triggered = True; break
    result = rep_state.get_winner()
    print(f"Triple repetition test - Winner: {result} (expected: -1 for draw, rep_triggered={rep_triggered})")
    assert result == -1 or rep_triggered, f"FAIL: repetition should have been triggered"

    print("\nAll special rule tests passed!")
    print("\nPopOut implementation test completed!")