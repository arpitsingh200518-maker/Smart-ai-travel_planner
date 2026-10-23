"""Random Forest classifier trained on synthetic preference-match profiles."""
import random
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from .features import rule_label

FEATURE_NAMES = ["interest_match", "climate_match", "group_match", "duration_fit", "scope_match"]

def synthetic_training_data(n_samples=1200, seed=42):
    rng = random.Random(seed)
    rows, labels = [], []
    for _ in range(n_samples):
        vector = [
            rng.choice([0.0, 0.25, 0.5, 0.75, 1.0]),
            rng.choice([0.0, 1.0]),
            rng.choice([0.0, 1.0]),
            rng.choice([0.0, 1.0]),
            rng.choice([0.0, 1.0]),
        ]
        rows.append(vector)
        labels.append(rule_label(vector))
    return pd.DataFrame(rows, columns=FEATURE_NAMES), labels

def train_model(seed=42):
    X, y = synthetic_training_data(seed=seed)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=seed, stratify=y)
    model = RandomForestClassifier(n_estimators=120, max_depth=7, random_state=seed, class_weight="balanced")
    model.fit(X_train, y_train)
    predicted = model.predict(X_test)
    metrics = {"synthetic_holdout_accuracy": float(accuracy_score(y_test, predicted)), "training_samples": len(X_train), "test_samples": len(X_test)}
    return model, metrics

def suitability_probability(model, vector):
    probabilities = model.predict_proba(pd.DataFrame([vector], columns=FEATURE_NAMES))[0]
    classes = list(model.classes_)
    return float(probabilities[classes.index(1)]) if 1 in classes else 0.0
