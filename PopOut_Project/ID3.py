"""
ID3 Decision Tree Implementation for PopOut and Iris datasets

Features:
  - id3()                      : recursive tree builder
  - predict_sample() / predict(): classification
  - print_tree()               : textual indented visualization
  - discretize_column()        : equal-width binning for continuous features
  - load_iris_data()           : load + discretize iris.csv
  - load_popout_data()         : load popout_pairs.csv
  - kfold_cross_validation()   : k-fold CV, returns per-fold and mean accuracy
  - compute_metrics()          : precision, recall, F1 per class
  - train_popout_tree()        : train on PopOut dataset
  - train_iris_tree()          : train on discretized Iris dataset
  - evaluate_tree()            : accuracy on test set
  - save_tree() / load_tree()  : JSON persistence
"""

import os
import json
import math
import random
import csv
import numpy as np
import pandas as pd
from collections import Counter

# ---------------------------------------------------------------------------
# File paths
# ---------------------------------------------------------------------------
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
DATA_DIR     = os.path.join(SCRIPT_DIR, 'data')
DATASET_FILE = os.path.join(DATA_DIR, 'popout_pairs.csv')
TREE_FILE    = os.path.join(DATA_DIR, 'popout_tree.json')
IRIS_FILE    = os.path.join(DATA_DIR, 'iris.csv')

# ---------------------------------------------------------------------------
# Core ID3 algorithm
# ---------------------------------------------------------------------------

def entropy(values):
    if hasattr(values, 'tolist'):
        values = values.tolist()
    if not values:
        return 0.0
    total = len(values)
    counts = Counter(values)
    ent = 0.0
    for c in counts.values():
        p = c / total
        if p > 0:
            ent -= p * math.log2(p)
    return ent


def information_gain(dataset, attribute, target_attr):
    total_entropy = entropy(dataset[target_attr])
    total = len(dataset)
    weighted = 0.0
    for val in dataset[attribute].unique():
        sub = dataset[dataset[attribute] == val]
        weighted += (len(sub) / total) * entropy(sub[target_attr])
    return total_entropy - weighted


def id3(dataset, attributes, target_attr, max_depth=None, min_samples_split=2, depth=0):
    """
    Build an ID3 decision tree recursively.

    Returns:
        Nested dict (internal node) or a leaf value (class label).
    """
    if len(dataset) < min_samples_split:
        return Counter(dataset[target_attr]).most_common(1)[0][0]

    if max_depth is not None and depth >= max_depth:
        return Counter(dataset[target_attr]).most_common(1)[0][0]

    classes = dataset[target_attr].unique()
    if len(classes) == 1:
        return classes[0]

    if not attributes:
        return Counter(dataset[target_attr]).most_common(1)[0][0]

    best_attr = max(attributes, key=lambda a: information_gain(dataset, a, target_attr))
    if information_gain(dataset, best_attr, target_attr) == 0:
        return Counter(dataset[target_attr]).most_common(1)[0][0]

    tree = {best_attr: {}}
    remaining = [a for a in attributes if a != best_attr]

    for val in dataset[best_attr].unique():
        sub = dataset[dataset[best_attr] == val]
        if len(sub) == 0:
            tree[best_attr][val] = Counter(dataset[target_attr]).most_common(1)[0][0]
        else:
            tree[best_attr][val] = id3(sub, remaining, target_attr, max_depth, min_samples_split, depth + 1)

    return tree


# ---------------------------------------------------------------------------
# Prediction
# ---------------------------------------------------------------------------

def predict_sample(tree, sample, default="unknown"):
    """Predict the class of a single sample dict."""
    if not isinstance(tree, dict):
        return tree

    root_attr = next(iter(tree))
    if root_attr not in sample:
        return default

    # Force string comparison — avoids int vs str mismatch
    attr_value = str(sample[root_attr])
    subtree = tree[root_attr]

    if attr_value not in subtree:
        return default

    return predict_sample(subtree[attr_value], sample, default)


def predict(tree, test_data):
    """Predict classes for all rows in a DataFrame."""
    preds = []
    for _, row in test_data.iterrows():
        sample = {k: str(v) for k, v in row.to_dict().items()}
        preds.append(predict_sample(tree, sample))
    return preds


# ---------------------------------------------------------------------------
# Tree visualisation
# ---------------------------------------------------------------------------

def print_tree(tree, indent=0, branch_label=""):
    """
    Print a human-readable indented representation of the tree.

    Example:
        c21
        ├── 0:
        │     c14
        │     ├── 1: drop
        │     └── 2: pop
        └── 1: drop
    """
    prefix = "    " * indent
    if branch_label:
        prefix_label = prefix + f"[{branch_label}] "
    else:
        prefix_label = prefix

    if not isinstance(tree, dict):
        print(f"{prefix_label}→ {tree}")
        return

    attr = next(iter(tree))
    print(f"{prefix_label}{attr}")
    children = list(tree[attr].items())
    for i, (val, subtree) in enumerate(children):
        connector = "└── " if i == len(children) - 1 else "├── "
        print(f"{prefix}{connector}{val}:")
        print_tree(subtree, indent + 1)


def tree_depth(tree):
    """Return maximum depth of the tree."""
    if not isinstance(tree, dict):
        return 0
    attr = next(iter(tree))
    return 1 + max((tree_depth(sub) for sub in tree[attr].values()), default=0)


def count_nodes(tree):
    """Return (leaves, internal_nodes)."""
    if not isinstance(tree, dict):
        return 1, 0
    attr = next(iter(tree))
    leaves = 0
    internal = 1
    for sub in tree[attr].values():
        l, i = count_nodes(sub)
        leaves += l
        internal += i
    return leaves, internal


# ---------------------------------------------------------------------------
# Discretisation (for continuous features like Iris)
# ---------------------------------------------------------------------------

def discretize_column(series, n_bins=4, labels=None):
    """
    Discretize a continuous pandas Series into equal-width bins.

    Args:
        series  : pandas Series with numeric values
        n_bins  : number of equal-width intervals
        labels  : optional list of bin labels (length = n_bins)

    Returns:
        pandas Series with string category labels
    """
    if labels is None:
        labels = [f"bin{i+1}" for i in range(n_bins)]
    min_v, max_v = series.min(), series.max()
    edges = [min_v + i * (max_v - min_v) / n_bins for i in range(n_bins + 1)]
    edges[-1] += 1e-9  # ensure max falls in last bin

    def _assign(v):
        for i in range(n_bins):
            if edges[i] <= v < edges[i + 1]:
                return str(labels[i])
        return str(labels[-1])

    return series.apply(_assign)


# ---------------------------------------------------------------------------
# Dataset loading
# ---------------------------------------------------------------------------

def load_iris_data(filename=IRIS_FILE, n_bins=4):
    """
    Load iris.csv and discretize the four continuous features.

    Bins (equal-width, 4 bins):
        'very_low', 'low', 'high', 'very_high'

    Returns:
        pandas DataFrame with discretized features and 'class' column.
    """
    if not os.path.exists(filename):
        print(f"Iris file not found: {filename}")
        return None

    df = pd.read_csv(filename)
    # Drop the ID column if present
    if 'ID' in df.columns:
        df = df.drop(columns=['ID'])

    cont_cols = ['sepallength', 'sepalwidth', 'petallength', 'petalwidth']
    bin_labels = ['muito_baixo', 'baixo', 'alto', 'muito_alto']

    for col in cont_cols:
        if col in df.columns:
            df[col] = discretize_column(df[col], n_bins=n_bins, labels=bin_labels)

    # Ensure class column exists
    if 'class' not in df.columns:
        print("Warning: 'class' column not found in iris.csv")

    return df


def load_popout_data(filename=DATASET_FILE):
    """
    Load PopOut dataset from CSV.
    Board columns c0-c41 are stored as strings (categorical).
    """
    if not os.path.exists(filename):
        print(f"Dataset file not found: {filename}")
        return None

    df = pd.read_csv(filename)
    board_cols = [f'c{i}' for i in range(42)]
    for col in board_cols:
        if col in df.columns:
            df[col] = df[col].astype(str)

    return df


# ---------------------------------------------------------------------------
# Training wrappers
# ---------------------------------------------------------------------------

def train_popout_tree(dataset, max_depth=None, min_samples_split=2):
    """Train ID3 on PopOut board data. Target: move_type (0=drop, 1=pop)."""
    if dataset is None or len(dataset) == 0:
        print("No dataset!")
        return None
    features = [f'c{i}' for i in range(42)]
    target = 'move_type'
    # Ensure move_type is string for consistency
    dataset = dataset.copy()
    dataset[target] = dataset[target].astype(str)
    print(f"Training PopOut tree: {len(dataset)} samples, max_depth={max_depth}")
    tree = id3(dataset, features, target, max_depth, min_samples_split)
    print("Done.")
    return tree


def train_iris_tree(dataset, max_depth=None, min_samples_split=2):
    """Train ID3 on discretized Iris data. Target: class."""
    if dataset is None or len(dataset) == 0:
        print("No dataset!")
        return None
    features = [c for c in dataset.columns if c != 'class']
    target = 'class'
    print(f"Training Iris tree: {len(dataset)} samples, max_depth={max_depth}")
    tree = id3(dataset, features, target, max_depth, min_samples_split)
    print("Done.")
    return tree


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def train_test_split_manual(df, test_size=0.2, random_state=42):
    """Simple manual train/test split."""
    np.random.seed(random_state)
    idx = list(df.index)
    np.random.shuffle(idx)
    n_test = int(len(idx) * test_size)
    return df.loc[idx[n_test:]], df.loc[idx[:n_test]]


def evaluate_tree(tree, test_data, target_col='move_type'):
    """Return accuracy on test_data."""
    if tree is None or test_data is None or len(test_data) == 0:
        return 0.0
    preds = predict(tree, test_data)
    actual = [str(v) for v in test_data[target_col].tolist()]
    correct = sum(p == a for p, a in zip(preds, actual))
    return correct / len(actual)


def kfold_cross_validation(dataset, features, target, k=5, max_depth=None, min_samples_split=2, random_state=42):
    """
    K-fold cross-validation.

    Returns:
        dict with 'fold_accuracies' list and 'mean_accuracy' float.
    """
    np.random.seed(random_state)
    idx = list(dataset.index)
    np.random.shuffle(idx)
    folds = [idx[i::k] for i in range(k)]

    fold_acc = []
    for i in range(k):
        test_idx = folds[i]
        train_idx = [x for j, fold in enumerate(folds) if j != i for x in fold]
        train_df = dataset.loc[train_idx]
        test_df  = dataset.loc[test_idx]
        tree = id3(train_df, features, target, max_depth, min_samples_split)
        acc = evaluate_tree(tree, test_df, target)
        fold_acc.append(acc)

    return {'fold_accuracies': fold_acc, 'mean_accuracy': float(np.mean(fold_acc))}


def compute_metrics(predictions, actual, classes=None):
    """
    Compute per-class precision, recall and F1, plus overall accuracy.

    Args:
        predictions : list of predicted labels (strings)
        actual      : list of true labels (strings)
        classes     : list of class names (inferred from data if None)

    Returns:
        dict: {class_name: {'precision', 'recall', 'f1'}, ..., 'accuracy': float}
    """
    predictions = [str(p) for p in predictions]
    actual       = [str(a) for a in actual]
    if classes is None:
        classes = sorted(set(actual) | set(predictions))

    results = {}
    for cls in classes:
        tp = sum(p == cls and a == cls for p, a in zip(predictions, actual))
        fp = sum(p == cls and a != cls for p, a in zip(predictions, actual))
        fn = sum(p != cls and a == cls for p, a in zip(predictions, actual))
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall    = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1        = (2 * precision * recall / (precision + recall)
                     if (precision + recall) > 0 else 0.0)
        results[cls] = {'precision': precision, 'recall': recall, 'f1': f1}

    correct = sum(p == a for p, a in zip(predictions, actual))
    results['accuracy'] = correct / len(actual) if actual else 0.0
    return results


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

class _NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        return super().default(obj)


def save_tree(tree, filename=TREE_FILE):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, 'w') as f:
        json.dump(tree, f, indent=2, cls=_NumpyEncoder)
    print(f"Tree saved → {filename}")


def load_tree(filename=TREE_FILE):
    if not os.path.exists(filename):
        print(f"Tree file not found: {filename}")
        return None
    with open(filename, 'r') as f:
        tree = json.load(f)
    print(f"Tree loaded ← {filename}")
    return tree


# ---------------------------------------------------------------------------
# Legacy helper (kept for backward compatibility)
# ---------------------------------------------------------------------------

def analyze_tree(tree, dataset=None):
    leaves, internal = count_nodes(tree)
    total = leaves + internal
    print(f"\nTree Analysis:")
    print(f"  Depth        : {tree_depth(tree)}")
    print(f"  Total nodes  : {total}")
    print(f"  Internal     : {internal}")
    print(f"  Leaves       : {leaves}")
    print(f"  Leaf ratio   : {leaves/total*100:.1f}%")


# ---------------------------------------------------------------------------
# CLI self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # ── Iris ────────────────────────────────────────────────────────────────
    print("=" * 60)
    print("IRIS DATASET (with discretisation)")
    print("=" * 60)
    iris = load_iris_data()
    if iris is not None:
        print(f"Samples: {len(iris)}")
        print(f"Columns: {list(iris.columns)}")
        print(f"\nClass distribution:\n{iris['class'].value_counts().to_string()}")
        print("\nFirst 3 rows after discretisation:")
        print(iris.head(3).to_string())

        feats = [c for c in iris.columns if c != 'class']
        cv = kfold_cross_validation(iris, feats, 'class', k=5, max_depth=None)
        print(f"\n5-fold CV mean accuracy: {cv['mean_accuracy']:.4f}")
        print(f"Per-fold: {[f'{a:.4f}' for a in cv['fold_accuracies']]}")

        train_i, test_i = train_test_split_manual(iris, test_size=0.2)
        tree_iris = train_iris_tree(train_i, max_depth=None)
        preds = predict(tree_iris, test_i)
        actual = [str(v) for v in test_i['class'].tolist()]
        m = compute_metrics(preds, actual)
        print(f"\nIris test accuracy: {m['accuracy']:.4f}")
        for cls in sorted(k for k in m if k != 'accuracy'):
            print(f"  {cls:20s}  P={m[cls]['precision']:.2f}  R={m[cls]['recall']:.2f}  F1={m[cls]['f1']:.2f}")

        print("\nIris decision tree (first 3 levels):")
        def _trim(t, d=0, max_d=3):
            if not isinstance(t, dict) or d >= max_d:
                return t if not isinstance(t, dict) else "..."
            attr = next(iter(t))
            return {attr: {v: _trim(s, d+1, max_d) for v, s in t[attr].items()}}
        print_tree(_trim(tree_iris))

    # ── PopOut ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("POPOUT DATASET")
    print("=" * 60)
    df = load_popout_data()
    if df is None:
        print("No popout dataset found. Run generate_popout_dataset.py first.")
    else:
        print(f"Samples: {len(df)}")
        mv = df['move_type'].value_counts()
        print(f"Drop (0): {mv.get(0, 0)}  Pop (1): {mv.get(1, 0)}")

        train_p, test_p = train_test_split_manual(df, test_size=0.2)
        tree_p = train_popout_tree(train_p, max_depth=8)
        preds_p = predict(tree_p, test_p)
        actual_p = [str(v) for v in test_p['move_type'].tolist()]
        m_p = compute_metrics(preds_p, actual_p)
        print(f"\nPopOut test accuracy : {m_p['accuracy']:.4f}")
        for cls in sorted(k for k in m_p if k != 'accuracy'):
            print(f"  Class {cls}  P={m_p[cls]['precision']:.2f}  R={m_p[cls]['recall']:.2f}  F1={m_p[cls]['f1']:.2f}")

        feats_p = [f'c{i}' for i in range(42)]
        df_copy = df.copy()
        df_copy['move_type'] = df_copy['move_type'].astype(str)
        cv_p = kfold_cross_validation(df_copy, feats_p, 'move_type', k=5, max_depth=8)
        print(f"\n5-fold CV mean accuracy (PopOut): {cv_p['mean_accuracy']:.4f}")

        save_tree(tree_p)
        analyze_tree(tree_p)

