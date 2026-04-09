#!/usr/bin/env python3
"""
Generate PopOut dataset using MCTS

This script generates training data for the ID3 decision tree by:
1. Using MCTS to play complete PopOut games
2. Recording (board_state, best_move) pairs
3. Saving to CSV for later training
"""

import os
import csv
import time
from PopOut import PopOutState, ROWS, COLS
from MCTS import MCTS

# CSV file path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR   = os.path.join(SCRIPT_DIR, 'data')
CSV_FILE   = os.path.join(DATA_DIR, 'popout_pairs.csv')

def generate_game_data(mcts_time_limit=0.5, max_games=10):
    """
    Generate training data from MCTS games

    Args:
        mcts_time_limit: Time limit per MCTS search (seconds)
        max_games: Maximum number of games to generate

    Returns:
        List of (board_flat, move_type, move_col) tuples
    """
    game_data = []
    mcts = MCTS(max_simulations=200, max_time=mcts_time_limit)

    for game_num in range(max_games):
        print(f"Generating game {game_num + 1}/{max_games}...")

        # Start new game
        state = PopOutState()
        game_moves = []

        while not state.is_game_over():
            # Get best move from MCTS
            best_move, win_rate = mcts.search(state)

            if best_move is None:
                print("No valid moves available - ending game")
                break

            # Record the state-move pair
            board_flat = state.get_board_flat()
            move_type = 0 if best_move[0] == 'drop' else 1  # 0=drop, 1=pop
            move_col = best_move[1]

            game_moves.append(board_flat + [move_type, move_col])

            # Make the move
            state = state.make_move(best_move)

        # Add all moves from this game to dataset
        game_data.extend(game_moves)

        winner = state.get_winner()
        print(f"  Game {game_num + 1} completed: {len(game_moves)} moves, winner: {winner}")

    return game_data

def save_to_csv(data, filename=CSV_FILE):
    """
    Save generated data to CSV file

    Args:
        data: List of [board_flat + [move_type, move_col]] lists
        filename: Output CSV filename
    """
    print(f"Saving {len(data)} samples to {filename}...")

    with open(filename, 'a', newline='') as f:
        writer = csv.writer(f)
        for row in data:
            writer.writerow(row)

    print(f"Dataset saved! Total samples: {len(data)}")

def analyze_dataset(filename=CSV_FILE):
    """
    Analyze the generated dataset

    Args:
        filename: CSV file to analyze
    """
    if not os.path.exists(filename):
        print(f"File {filename} does not exist")
        return

    print(f"\nAnalyzing dataset: {filename}")

    # Read all data
    data = []
    with open(filename, 'r') as f:
        reader = csv.reader(f)
        next(reader)  # Skip header
        for row in reader:
            data.append([int(x) for x in row])

    if not data:
        print("No data found")
        return

    print(f"Total samples: {len(data)}")

    # Analyze move types
    drop_moves = sum(1 for row in data if row[-2] == 0)
    pop_moves = sum(1 for row in data if row[-2] == 1)

    print(f"Drop moves: {drop_moves} ({drop_moves/len(data)*100:.1f}%)")
    print(f"Pop moves: {pop_moves} ({pop_moves/len(data)*100:.1f}%)")

    # Analyze column distribution
    col_counts = {}
    for row in data:
        col = row[-1]
        col_counts[col] = col_counts.get(col, 0) + 1

    print("Moves per column:")
    for col in range(COLS):
        count = col_counts.get(col, 0)
        print(f"  Column {col}: {count} moves")

if __name__ == "__main__":
    print("PopOut Dataset Generator")
    print("=" * 40)

    # Parameters
    MCTS_TIME = 0.3  # seconds per move
    N_GAMES = 5      # number of games to generate

    print(f"MCTS time limit: {MCTS_TIME}s per move")
    print(f"Games to generate: {N_GAMES}")
    print()

    # Generate data
    start_time = time.time()
    game_data = generate_game_data(MCTS_TIME, N_GAMES)
    generation_time = time.time() - start_time

    print(f"Generation time: {generation_time:.2f}s")
    print(f"Samples generated: {len(game_data)}")

    # Save to CSV
    save_to_csv(game_data)

    # Analyze dataset
    analyze_dataset()

    print("\nDataset generation completed!")
    print(f"Output file: {CSV_FILE}")