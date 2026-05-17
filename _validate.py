"""Quick validation of all modules."""
import sys
errors = []

try:
    from PopOut import PopOutState
    s = PopOutState()
    s2 = s.make_move(('drop', 3))
    print('PopOut.py OK')
except Exception as e:
    errors.append(f'PopOut: {e}')

try:
    from MCTS import MCTS, MCTSHeuristic, MCTSTopK, run_games, search_convergence
    mcts = MCTS(max_simulations=10, max_time=0.1)
    move, wr = mcts.search(PopOutState())
    print(f'MCTS.py OK (move={move}, wr={wr:.3f})')

    mh = MCTSHeuristic(max_simulations=10, max_time=0.1)
    move2, wr2 = mh.search(PopOutState())
    print(f'MCTSHeuristic OK (move={move2}, wr={wr2:.3f})')

    mk = MCTSTopK(k=2, max_simulations=10, max_time=0.1)
    move3, wr3 = mk.search(PopOutState())
    print(f'MCTSTopK OK (move={move3}, wr={wr3:.3f})')
except Exception as e:
    errors.append(f'MCTS: {e}')
    import traceback; traceback.print_exc()

try:
    from ID3 import (load_iris_data, discretize_column, kfold_cross_validation,
                     compute_metrics, print_tree, tree_depth)
    iris = load_iris_data()
    print(f'ID3.py OK — iris={len(iris)} amostras')
    iris_feats = [c for c in iris.columns if c != 'class']
    cv = kfold_cross_validation(iris, iris_feats, 'class', k=3)
    mean_acc = cv['mean_accuracy']
    print(f'  CV 3-fold mean acc: {mean_acc:.4f}')
except Exception as e:
    errors.append(f'ID3: {e}')
    import traceback; traceback.print_exc()

if errors:
    print('ERROS:', errors)
else:
    print('\nTodos os módulos validados com sucesso!')
