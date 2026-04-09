from PopOut import GameState
from MCTS import MCTS

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
