#!/usr/bin/env python3
"""
generate_popout_dataset_strong.py
──────────────────────────────────
Versão "overnight" do gerador de dataset PopOut.

Usa MCTSHeuristic com mais simulações e mais jogos para produzir dados
de maior qualidade. Os dados são guardados em data/popout_pairs_strong.csv
(não sobrescreve o ficheiro original).

Estimativa de tempo: ~1-2 horas para 500 jogos com 1000 simulações.
"""

import os, csv, time
from collections import Counter
from PopOut import PopOutState, ROWS, COLS
from MCTS import MCTSHeuristic

# ── Parâmetros ──────────────────────────────────────────────────────────────
MCTS_SIMS  = 1000   # simulações por jogada  (original: 500)
MCTS_TIME  = 0.5    # segundos máx por jogada (original: 0.1)
N_GAMES    = 500    # jogos totais            (original: 200)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR   = os.path.join(SCRIPT_DIR, 'data')
CSV_FILE   = os.path.join(DATA_DIR, 'popout_pairs_strong.csv')
HEADER     = [f'c{i}' for i in range(ROWS * COLS)] + ['move']
# ────────────────────────────────────────────────────────────────────────────


def generate_game_data():
    game_data = []
    skipped   = 0
    mcts = MCTSHeuristic(
        max_simulations=MCTS_SIMS,
        max_time=MCTS_TIME,
        exploration_constant=1.4,
    )

    t_total = time.time()
    for game_num in range(N_GAMES):
        t_game = time.time()
        state  = PopOutState()
        game_moves = []

        while not state.is_game_over():
            best_move, _ = mcts.search(state)
            if best_move is None:
                break
            board_flat = state.get_board_flat()
            move_str   = f"{best_move[0]}_{best_move[1]}"
            game_moves.append(board_flat + [move_str])
            state = state.make_move(best_move)

        winner  = state.get_winner()
        elapsed = time.time() - t_game

        if winner in [1, 2]:
            game_data.extend(game_moves)
            eta = (time.time() - t_total) / (game_num + 1) * (N_GAMES - game_num - 1)
            print(f"  [{game_num+1:>3}/{N_GAMES}] {len(game_moves):>3} movimentos  "
                  f"vencedor={winner}  {elapsed:.1f}s  ETA {eta/60:.0f}min")
        else:
            skipped += 1
            print(f"  [{game_num+1:>3}/{N_GAMES}] skipped (empate/ciclo)")

    print(f"\nJogos ignorados: {skipped}/{N_GAMES}")
    return game_data


def deduplicate(data):
    seen, unique = set(), []
    for row in data:
        key = tuple(row)
        if key not in seen:
            seen.add(key)
            unique.append(row)
    removed = len(data) - len(unique)
    print(f"  Deduplicação: removidos {removed} ({removed/max(len(data),1)*100:.1f}%)")
    return unique


def save_to_csv(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    print(f"A guardar {len(data)} amostras → {CSV_FILE}")
    with open(CSV_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(HEADER)
        for row in data:
            writer.writerow(row)
    print("Guardado.")


def analyze(data):
    moves = [row[-1] for row in data]
    counts = Counter(moves)
    print(f"\nTotal amostras : {len(data)}")
    print(f"Drop           : {sum(v for k,v in counts.items() if k.startswith('drop'))}")
    print(f"Pop            : {sum(v for k,v in counts.items() if k.startswith('pop'))}")
    print("\nDistribuição por classe:")
    for move, cnt in sorted(counts.items()):
        bar = '█' * (cnt // 100)
        print(f"  {move:>8}: {cnt:>5}  {bar}")


if __name__ == '__main__':
    print("=" * 55)
    print("PopOut Dataset Generator — Versão Strong (Overnight)")
    print("=" * 55)
    print(f"  Simulações por jogada : {MCTS_SIMS}")
    print(f"  Tempo máx por jogada  : {MCTS_TIME}s")
    print(f"  Número de jogos       : {N_GAMES}")
    print(f"  Output                : {CSV_FILE}")
    print(f"  Estimativa            : {N_GAMES * 60 * MCTS_TIME / 60:.0f}–{N_GAMES * 80 * MCTS_TIME / 60:.0f} minutos")
    print()

    t0   = time.time()
    data = generate_game_data()

    print("\nA deduplicar...")
    data = deduplicate(data)
    analyze(data)
    save_to_csv(data)

    print(f"\nTempo total: {(time.time()-t0)/3600:.2f} horas")
