import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


# ============================================================
# TRADEMIND AI - TRUSTED ML TRAINING ENGINE
# ============================================================
# Review-1 version:
# - chronological train/test split
# - trusted 19-feature set from feature ablation
# - excludes suspicious outcome-derived behavior features
# - duplicate symbol/direction columns are removed
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[3]

INPUT_FILE = BASE_DIR / "data" / "ml_dataset.csv"
MODEL_DIR = BASE_DIR / "models"
MODEL_FILE = MODEL_DIR / "trade_outcome_model_trusted.joblib"
METRICS_FILE = MODEL_DIR / "trusted_training_metrics.json"
FEATURE_FILE = MODEL_DIR / "trusted_model_features.json"

TEST_SIZE = 0.20
RANDOM_STATE = 42
TARGET = "target"

# This is the Review-1 trusted feature set corresponding to the
# E_Full_Trusted ablation experiment already present in the project.
TRUSTED_FEATURES = [
    "symbol",
    "direction",
    "entry_hour",
    "entry_minute",
    "day_of_week_num",
    "trades_today",
    "time_since_previous_trade",
    "previous_position_size",
    "position_size_change_pct",
    "average_position_size",
    "position_size_ratio",
    "previous_trade_pnl",
    "previous_trade_is_loss",
    "previous_trade_is_win",
    "previous_loss_streak",
    "previous_session_pnl",
    "behavior_overtrading",
    "behavior_rapid_reentry",
    "behavior_oversizing",
]


# ============================================================
# LOAD DATA
# ============================================================

def load_dataset():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"ML dataset not found: {INPUT_FILE}")

    df = pd.read_csv(INPUT_FILE)
    print(f"Loaded ML records: {len(df):,}")
    return df


# ============================================================
# PREPARE DATA
# ============================================================

def prepare_data(df):
    df = df.copy()

    if TARGET not in df.columns:
        raise ValueError("Target column not found in ML dataset.")

    df["entry_time"] = pd.to_datetime(df["entry_time"], errors="coerce")

    if df["entry_time"].isna().any():
        raise ValueError("Invalid entry_time values detected.")

    # Trading data must be evaluated chronologically.
    df = df.sort_values("entry_time").reset_index(drop=True)

    missing = [feature for feature in TRUSTED_FEATURES if feature not in df.columns]
    if missing:
        raise ValueError(f"Trusted features missing from dataset: {missing}")

    X = df[TRUSTED_FEATURES].copy()
    y = df[TARGET].astype(int).copy()

    # Explicitly remove exact duplicate data columns if they appear.
    duplicate_columns = X.columns[X.columns.duplicated()].tolist()
    if duplicate_columns:
        X = X.loc[:, ~X.columns.duplicated()]

    print(f"Trusted features: {len(X.columns)}")
    for feature in X.columns:
        print(f"- {feature}")

    return df, X, y


# ============================================================
# CHRONOLOGICAL SPLIT
# ============================================================

def chronological_split(df, X, y):
    split_index = int(len(df) * (1 - TEST_SIZE))

    X_train = X.iloc[:split_index].copy()
    X_test = X.iloc[split_index:].copy()
    y_train = y.iloc[:split_index].copy()
    y_test = y.iloc[split_index:].copy()

    train_df = df.iloc[:split_index]
    test_df = df.iloc[split_index:]

    print("\n========== TEMPORAL SPLIT ==========")
    print(f"Training records: {len(X_train):,}")
    print(f"Testing records : {len(X_test):,}")
    print(f"Training period : {train_df['entry_time'].min()} → {train_df['entry_time'].max()}")
    print(f"Testing period  : {test_df['entry_time'].min()} → {test_df['entry_time'].max()}")

    return X_train, X_test, y_train, y_test


# ============================================================
# PIPELINE
# ============================================================

def build_pipeline(X_train):
    categorical_columns = X_train.select_dtypes(
        include=["object", "string"]
    ).columns.tolist()

    numerical_columns = X_train.select_dtypes(
        include=[np.number]
    ).columns.tolist()

    numerical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )

    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("encoder", OneHotEncoder(handle_unknown="ignore")),
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("numeric", numerical_pipeline, numerical_columns),
            ("categorical", categorical_pipeline, categorical_columns),
        ]
    )

    model = LogisticRegression(
        max_iter=2000,
        class_weight="balanced",
        random_state=RANDOM_STATE,
    )

    return Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("model", model),
        ]
    )


# ============================================================
# EVALUATION
# ============================================================

def evaluate_model(model, X_test, y_test):
    predictions = model.predict(X_test)
    probabilities = model.predict_proba(X_test)[:, 1]

    accuracy = accuracy_score(y_test, predictions)
    precision = precision_score(y_test, predictions, zero_division=0)
    recall = recall_score(y_test, predictions, zero_division=0)
    f1 = f1_score(y_test, predictions, zero_division=0)
    roc_auc = roc_auc_score(y_test, probabilities)
    pr_auc = average_precision_score(y_test, probabilities)
    cm = confusion_matrix(y_test, predictions)

    print("\n========== TRUSTED MODEL EVALUATION ==========")
    print(f"Accuracy : {accuracy:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall   : {recall:.4f}")
    print(f"F1 Score : {f1:.4f}")
    print(f"ROC-AUC  : {roc_auc:.4f}")
    print(f"PR-AUC   : {pr_auc:.4f}")
    print("\nConfusion Matrix:")
    print(cm)
    print("\nClassification Report:")
    print(
        classification_report(
            y_test,
            predictions,
            target_names=["Loss", "Win"],
            zero_division=0,
        )
    )

    return {
        "validation_type": "chronological_holdout",
        "trusted_feature_set": "E_Full_Trusted",
        "feature_count": len(TRUSTED_FEATURES),
        "accuracy": float(accuracy),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "roc_auc": float(roc_auc),
        "pr_auc": float(pr_auc),
        "test_records": int(len(y_test)),
        "test_wins": int((y_test == 1).sum()),
        "test_losses": int((y_test == 0).sum()),
        "confusion_matrix": cm.tolist(),
    }


# ============================================================
# SAVE
# ============================================================

def save_outputs(model, metrics):
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    joblib.dump(model, MODEL_FILE)

    with open(METRICS_FILE, "w", encoding="utf-8") as file:
        json.dump(metrics, file, indent=4)

    feature_metadata = {
        "feature_count": len(TRUSTED_FEATURES),
        "feature_set": "E_Full_Trusted",
        "features": TRUSTED_FEATURES,
        "excluded_suspicious_features": [
            "win_streak",
            "loss_streak",
            "behavior_loss_streak",
            "behavior_revenge",
        ],
        "duplicate_columns_removed": [
            "symbol.1",
            "direction.1",
        ],
    }

    with open(FEATURE_FILE, "w", encoding="utf-8") as file:
        json.dump(feature_metadata, file, indent=4)

    print(f"\nSaved trusted model: {MODEL_FILE}")
    print(f"Saved trusted metrics: {METRICS_FILE}")
    print(f"Saved feature metadata: {FEATURE_FILE}")


# ============================================================
# MAIN
# ============================================================

def main():
    print("\n========== TRADEMIND AI ==========")
    print("Starting trusted ML training...")

    df = load_dataset()
    df, X, y = prepare_data(df)
    X_train, X_test, y_train, y_test = chronological_split(df, X, y)

    pipeline = build_pipeline(X_train)

    print("\n========== MODEL TRAINING ==========")
    print("Training Logistic Regression on trusted features...")
    pipeline.fit(X_train, y_train)

    metrics = evaluate_model(pipeline, X_test, y_test)
    save_outputs(pipeline, metrics)

    print("\n====================================")
    print("TRUSTED ML TRAINING COMPLETE")
    print("====================================\n")


if __name__ == "__main__":
    main()
