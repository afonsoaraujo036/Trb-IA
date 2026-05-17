#!/usr/bin/env python3
import os
import csv
from ConnectFour import ConnectFourState, PureMCTS

# ─── Caminho para o arquivo CSV ───
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE = os.path.join(SCRIPT_DIR, 'connect4_pairs.csv')

# ─── Criação do arquivo CSV ───
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        # Cabeçalho: 42 posições do tabuleiro + movimento
        header = [f'c{i}' for i in range(42)] + ['move']
        writer.writerow(header)

def generate_game_records(time_limit=0.5):
    """
    Simula um jogo completo com PureMCTS e retorna uma lista de pares (estado, movimento).
    """
    # Estado inicial vazio
    board = [[0] * 7 for _ in range(6)]
    vazios = [5] * 7
    state = ConnectFourState(board, vazios, current_player=1)

    records = []
    while not state.is_game_over():
        # Converte o tabuleiro para uma lista linear (42 elementos)
        flat_board = [cell for row in state.board for cell in row]

        # Usa MCTS para escolher a melhor jogada
        player = state.get_current_player()
        mcts = PureMCTS(state, player, time_limit=time_limit)
        move = mcts.get_best_move()

        # Guarda o par (estado atual, jogada)
        records.append(flat_board + [move])

        # Atualiza o estado com a jogada escolhida
        state = state.make_move(move)

    return records

if __name__ == "__main__":
    N_GAMES = 100  # Número de jogos para gerar o dataset
    with open(CSV_FILE, 'a', newline='') as f:
        writer = csv.writer(f)
        for game_number in range(1, N_GAMES + 1):
            records = generate_game_records(time_limit=0.5)
            for row in records:
                writer.writerow(row)
            print(f"Jogo {game_number}/{N_GAMES} gravado com {len(records)} jogadas.")
    print("Dataset gerado e salvo em", CSV_FILE)
