import pandas as pd
import numpy as np 
import math
from collections import Counter
from sklearn.model_selection import train_test_split, KFold, cross_val_score
from sklearn.metrics import confusion_matrix, accuracy_score
import matplotlib.pyplot as plt
from sklearn.tree import DecisionTreeClassifier, plot_tree
import uuid
import os 

# ---------------------------------------------
# 0. Funções auxiliares (entropia, ganho, classificar)
# ---------------------------------------------
def entropia(valores):
    total = len(valores)
    contagem = Counter(valores)
    return -sum((freq / total) * math.log2(freq / total) for freq in contagem.values())

def ganho_informacao(dataset, atributo, alvo):
    ent_total = entropia(dataset[alvo])
    soma = 0
    for val in dataset[atributo].unique():
        sub = dataset[dataset[atributo] == val]
        soma += (len(sub)/len(dataset)) * entropia(sub[alvo])
    return ent_total - soma

# ---------------------------------------------
# 1. Leitura e discretização do iris.csv
# ---------------------------------------------
script_dir = os.path.dirname(os.path.abspath(__file__))
csv_path   = os.path.join(script_dir, 'iris.csv')
df = pd.read_csv(csv_path)
if 'ID' in df.columns:
    df = df.drop(columns=['ID'])
bins   = 3
labels = ['baixo','médio','alto']
for col in ['sepallength','sepalwidth','petallength','petalwidth']:
    df[col] = pd.qcut(df[col], q=bins, labels=labels)

atributos = [c for c in df.columns if c!='class']

# ---------------------------------------------
# 2. Definição do ID3 (com ou sem poda)
# ---------------------------------------------
# Se quiseres poda, substitui esta definição pela versão com max_depth/min_samples_leaf:
def id3(dataset, atributos, alvo, max_depth=None, min_samples_leaf=1, depth=0):
    classes = dataset[alvo].tolist()
    if len(set(classes)) == 1:
        return classes[0]
    if (not atributos
        or (max_depth is not None and depth >= max_depth)
        or len(dataset) < 2*min_samples_leaf):
        return Counter(classes).most_common(1)[0][0]
    best = max(atributos, key=lambda a: ganho_informacao(dataset,a,alvo))
    tree = {best:{}}
    for v in dataset[best].unique():
        sub = dataset[dataset[best]==v]
        if len(sub) < min_samples_leaf:
            tree[best][v] = Counter(classes).most_common(1)[0][0]
        else:
            tree[best][v] = id3(sub,
                                [a for a in atributos if a!=best],
                                alvo,
                                max_depth,
                                min_samples_leaf,
                                depth+1)
    return tree

def classificar(inst, arvore):
    if not isinstance(arvore, dict):
        return arvore
    atb = next(iter(arvore))
    v   = inst.get(atb)
    return (classificar(inst, arvore[atb][v])
            if v in arvore[atb] else None)

# ---------------------------------------------
# 3. Avaliação manual: hold-out 80/20
# ---------------------------------------------
df_train, df_test = train_test_split(df, test_size=0.2, random_state=42)
arvore = id3(df_train, atributos, "class")
prevs  = [classificar(r.to_dict(), arvore) for _,r in df_test.iterrows()]
reais  = df_test["class"].tolist()
valid  = [(p,r) for p,r in zip(prevs, reais) if p is not None]
acc    = accuracy_score([p for p,_ in valid], [r for _,r in valid])
print("Acurácia hold-out:", round(acc*100,2),"%")
print("Matriz de confusão:")
print(confusion_matrix([r for _,r in valid],[p for p,_ in valid],
                       labels=sorted(df["class"].unique())))

# ---------------------------------------------
# 4. k-Fold Cross-Validation do teu ID3
# ---------------------------------------------
def cross_val_score_id3(df, atributos, alvo, k=5, random_state=42):
    kf = KFold(n_splits=k, shuffle=True, random_state=random_state)
    scores = []
    for tr_idx, te_idx in kf.split(df):
        tr  = df.iloc[tr_idx]; te = df.iloc[te_idx]
        arv = id3(tr, atributos, alvo)    # ou passar max_depth, min_samples_leaf
        ps  = [classificar(r.to_dict(), arv) for _,r in te.iterrows()]
        rs  = te[alvo].tolist()
        v   = [(p,r) for p,r in zip(ps, rs) if p is not None]
        scores.append(accuracy_score([p for p,_ in v],[r for _,r in v]))
    return scores

scores = cross_val_score_id3(df, atributos, "class", k=5)
print(f"CV 5-fold: {np.mean(scores)*100:.2f}% ± {np.std(scores)*100:.2f}%")

# ---------------------------------------------
# 5. Comparação com sklearn + visualização
# ---------------------------------------------
# (transforma as categorias em dummy variables)
X = pd.get_dummies(df[atributos])
y = df["class"]

clf = DecisionTreeClassifier(criterion="entropy",
                             max_depth=None,
                             min_samples_leaf=1,
                             random_state=42)
scores_skl = cross_val_score(clf, X, y, cv=5)
print(f"sklearn CV: {scores_skl.mean()*100:.2f}% ± {scores_skl.std()*100:.2f}%")

# treina e desenha a árvore
clf.fit(X, y)
plt.figure(figsize=(12,8))
plot_tree(clf,
          feature_names=X.columns,
          class_names=clf.classes_,
          filled=True, rounded=True, fontsize=8)


plt.tight_layout()
plt.show(block=False)
           #  fecha a figura e desbloqueia o script, para ver é só retirar "block=False" da linha anterior

# ---------------------------------------------
# 6. Grid-search para otimização de hiper-parâmetros
# ---------------------------------------------
from sklearn.model_selection import GridSearchCV
from sklearn.tree import DecisionTreeClassifier

print("→ Começando GridSearch…")    # agora vais ver este print imediatamente

param_grid = {
    'max_depth':        [2, 3, 4, None],
    'min_samples_leaf': [1, 2, 5, 10]
}

grid = GridSearchCV(
    DecisionTreeClassifier(criterion='entropy', random_state=42),
    param_grid,
    cv=5,
    scoring='accuracy',
    n_jobs=-1
)

grid.fit(X, y)

print("→ GridSearch terminado.")
print("Melhores parâmetros:", grid.best_params_)
print(f"Melhor acurácia em CV: {grid.best_score_*100:.2f}%")