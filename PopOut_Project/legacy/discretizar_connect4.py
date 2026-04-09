#!/usr/bin/env python3
import pandas as pd
import os
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.metrics import accuracy_score, confusion_matrix
import matplotlib.pyplot as plt

# ---------------------------------------------
# 1. Leitura do CSV gerado no Connect Four
# ---------------------------------------------
script_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(script_dir, 'connect4_pairs.csv')

# Carregar o conjunto de dados
df = pd.read_csv(csv_path)

# Definir os atributos e o alvo
atributos = [f'c{i}' for i in range(42)]
alvo = 'move'

# Criar as variáveis X e y
X = df[atributos]
y = df[alvo]

# Verificação rápida dos dados
print("Dados carregados e prontos para uso:")
print(df.head())

# ---------------------------------------------
# 2. Divisão treino/teste
# ---------------------------------------------
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# ---------------------------------------------
# 3. Otimização com GridSearchCV
# ---------------------------------------------
param_grid = {
    'max_depth': [5, 10, 15, 20, None],
    'min_samples_leaf': [1, 2, 5, 10],
    'criterion': ['gini', 'entropy'],
    'ccp_alpha': [0.0, 0.01, 0.05, 0.1]
}

print("→ Iniciando GridSearch para otimização de hiperparâmetros...")

grid = GridSearchCV(
    DecisionTreeClassifier(random_state=42),
    param_grid,
    cv=5,
    scoring='accuracy',
    n_jobs=-1
)

grid.fit(X_train, y_train)

# Melhor estimador encontrado
best_clf = grid.best_estimator_
print("Melhores parâmetros encontrados:", grid.best_params_)

# Avaliação no conjunto de teste
y_pred = best_clf.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)
print(f"Acurácia no conjunto de teste (após otimização): {accuracy * 100:.2f}%")
print("Matriz de Confusão:")
print(confusion_matrix(y_test, y_pred))

# Visualização da árvore otimizada
plt.figure(figsize=(20, 10))
from sklearn.tree import plot_tree
plot_tree(best_clf, feature_names=atributos, class_names=[str(i) for i in range(7)], filled=True, rounded=True)
plt.title("Árvore de Decisão Otimizada - Connect Four")
plt.show()

