#!/usr/bin/env python3
"""
Generate PopOut dataset using MCTS

This script generates training data for the ID3 decision tree by:
1. Using MCTS to play complete PopOut games
2. Recording (board_state, move) pairs where move = "drop_3" or "pop_2"
3. Saving to CSV for later training
"""

import os
import csv
import time
from collections import Counter
from PopOut import PopOutState, ROWS, COLS
from MCTS import MCTS, MCTSHeuristic


# CSV file path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR   = os.path.join(SCRIPT_DIR, 'data')
CSV_FILE   = os.path.join(DATA_DIR, 'popout_pairs.csv')

# Cabeçalho do CSV: 42 células + move completo (string única)
HEADER = [f'c{i}' for i in range(ROWS * COLS)] + ['move']


def generate_game_data(mcts_time_limit=0.1, max_games=200):
    """
    Generate training data from MCTS games.
    """
    game_data = []
    skipped   = 0
    mcts = MCTSHeuristic(max_simulations=500, max_time=mcts_time_limit, exploration_constant=1.4)

    for game_num in range(max_games):
        print(f"Generating game {game_num + 1}/{max_games}...")

        state = PopOutState()   
        game_moves = []

        while not state.is_game_over():
            best_move, win_rate = mcts.search(state)

            if best_move is None:
                print("  No valid moves — ending game early")
                break

            # board flat: 42 integers (0=empty, 1=P1, 2=P2)
            board_flat = state.get_board_flat()

            # movimento completo como string única: ex: "drop_3" ou "pop_2"
            move_str = f"{best_move[0]}_{best_move[1]}"

            # Guarda o estado atual + a jogada escolhida pelo MCTS
            game_moves.append(board_flat + [move_str])

            state = state.make_move(best_move)

        winner = state.get_winner()

        # ignora jogos que terminaram só por limite de movimentos sem vencedor
        if winner in [1, 2]:
            game_data.extend(game_moves)
            print(f"  Game {game_num + 1}: {len(game_moves)} moves, winner: {winner}")
        else:
            skipped += 1
            reason = "ciclo" if winner == 0 else "erro/inválido"
            print(f"  Game {game_num + 1}: {len(game_moves)} moves, winner: {winner} (skipped — {reason})")
            continue


    print(f"\nTotal games skipped (ciclos): {skipped}/{max_games}")
    return game_data


def deduplicate(data):
    """Remove linhas duplicadas (mesmo estado + mesmo movimento)."""
    seen   = set()
    unique = []
    for row in data:
        key = tuple(row)
        if key not in seen:
            seen.add(key)
            unique.append(row)
    removed = len(data) - len(unique)
    if removed:
        print(f"  Deduplication: removed {removed} duplicates ({removed/len(data)*100:.1f}%)")
    return unique


def save_to_csv(data, filename=CSV_FILE, append=False):
    """
    Guarda os dados em CSV.
    Se append=False, remove o ficheiro antigo e escreve cabeçalho novo.
    """
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    # Se não for append, removemos o ficheiro antigo para garantir limpeza total
    if not append and os.path.exists(filename):
        os.remove(filename)

    mode = 'a' if append else 'w'
    write_header = not append

    print(f"{'Appending' if append else 'Saving'} {len(data)} samples → {filename}")
    with open(filename, mode, newline='') as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(HEADER)
        for row in data:
            writer.writerow(row)

    print(f"Done.")


def analyze_dataset(filename=CSV_FILE):
    """Analisa e imprime estatísticas do dataset."""
    if not os.path.exists(filename):
        print(f"File not found: {filename}")
        return

    print(f"\nAnalyzing: {filename}")

    rows = []
    with open(filename, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    if not rows:
        print("No data found.")
        return

    print("-" * 40)
    print(f"Total samples : {len(rows)}")

    # contagem por tipo de movimento
    move_counts = Counter(r['move'] for r in rows)

    drop_total = sum(v for k, v in move_counts.items() if k.startswith('drop'))
    pop_total  = sum(v for k, v in move_counts.items() if k.startswith('pop'))
    
    print(f"Drop moves    : {drop_total} ({drop_total/len(rows)*100:.1f}%)")
    print(f"Pop  moves    : {pop_total}  ({pop_total/len(rows)*100:.1f}%)")

    print("\nMoves per column:")
    for col in range(COLS):
        d = move_counts.get(f'drop_{col}', 0)
        p = move_counts.get(f'pop_{col}',  0)
        print(f"  Col {col}: drop={d:4d}  pop={p:4d}  total={d+p:4d}")

    print("\nTop 5 most common moves:")
    for move, cnt in move_counts.most_common(5):
        print(f"  {move:10s}: {cnt}")


if __name__ == "__main__":
    print("PopOut Dataset Generator (ID3 Format)")
    print("=" * 40)

    # ── Parâmetros de Produção ──────────────────────────────────────────────
    MCTS_TIME = 0.1
    N_GAMES   = 200  # Número de jogos completos a gerar
    APPEND    = False  # False garante que o formato antigo é apagado

    print(f"MCTS time limit : {MCTS_TIME}s per move")
    print(f"Games           : {N_GAMES}")
    print(f"Append mode     : {APPEND}")
    print()

    start_time = time.time()
    
    # Gerar os dados
    raw_data = generate_game_data(MCTS_TIME, N_GAMES)
    
    # Remover duplicados para a árvore não viciar em estados repetidos
    clean_data = deduplicate(raw_data)
    
    # Gravar no ficheiro
    save_to_csv(clean_data, append=APPEND)
    
    # Mostrar estatísticas finais
    analyze_dataset()

    elapsed = time.time() - start_time
    print(f"\nTotal time: {elapsed:.2f}s")
    print(f"Output: {CSV_FILE}")
