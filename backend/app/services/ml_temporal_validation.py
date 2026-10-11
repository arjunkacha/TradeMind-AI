import json
from pathlib import Path

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
# TRADEMIND AI - TEMPORAL ML VALIDATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[3]

INPUT_FILE = BASE_DIR / "data" / "ml_dataset.csv"
OUTPUT_FILE = BASE_DIR / "models" / "temporal_validation_metrics.json"


# ============================================================
# CONFIGURATION
# ============================================================

TEST_SIZE = 0.20

TARGET = "target"

# These are intentionally excluded because they deserve
# separate investigation before being trusted by the model.
SUSPICIOUS_FEATURES = {
    "loss_streak",
    "win_streak",
    "behavior_loss_streak",
    "behavior_revenge",
}

ID_COLUMNS = {
    "trade_id",
    "account",
    "entry_time",
    "target",
}


# ============================================================
# LOAD DATA
# ============================================================

def load_dataset():

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"ML dataset not found: {INPUT_FILE}"
        )

    df = pd.read_csv(INPUT_FILE)

    print(
        f"Loaded ML records: {len(df):,}"
    )

    return df


# ============================================================
# PREPARE DATA
# ============================================================

def prepare_data(df):

    print("\nPreparing temporal dataset...")

    df["entry_time"] = pd.to_datetime(
        df["entry_time"],
        errors="coerce"
    )

    if df["entry_time"].isna().any():
        raise ValueError(
            "Invalid entry_time values detected."
        )

    # Critical:
    # enforce chronological ordering.
    df = (
        df.sort_values("entry_time")
        .reset_index(drop=True)
    )

    feature_columns = [
        column
        for column in df.columns
        if column not in ID_COLUMNS
        and column not in SUSPICIOUS_FEATURES
    ]

    X = df[feature_columns].copy()
    y = df[TARGET].copy()

    return df, X, y, feature_columns


# ============================================================
# TEMPORAL SPLIT
# ============================================================

def temporal_split(df, X, y):

    split_index = int(
        len(df) * (1 - TEST_SIZE)
    )

    X_train = X.iloc[:split_index]
    X_test = X.iloc[split_index:]

    y_train = y.iloc[:split_index]
    y_test = y.iloc[split_index:]

    train_df = df.iloc[:split_index]
    test_df = df.iloc[split_index:]

    print("\n========== TEMPORAL SPLIT ==========")

    print(
        f"Training records: {len(X_train):,}"
    )

    print(
        f"Testing records : {len(X_test):,}"
    )

    print(
        f"\nTraining period:"
        f"\n{train_df['entry_time'].min()}"
        f"\n→ {train_df['entry_time'].max()}"
    )

    print(
        f"\nTesting period:"
        f"\n{test_df['entry_time'].min()}"
        f"\n→ {test_df['entry_time'].max()}"
    )

    print("\nTraining target distribution:")

    print(
        y_train.value_counts()
    )

    print("\nTesting target distribution:")

    print(
        y_test.value_counts()
    )

    return (
        X_train,
        X_test,
        y_train,
        y_test
    )


# ============================================================
# PREPROCESSING
# ============================================================

def build_pipeline(X_train):

    categorical_columns = (
        X_train
        .select_dtypes(
            include=["object", "string"]
        )
        .columns
        .tolist()
    )

    numerical_columns = (
        X_train
        .select_dtypes(
            include=[np.number]
        )
        .columns
        .tolist()
    )

    print(
        "\n========== PREPROCESSING =========="
    )

    print(
        f"Categorical features: "
        f"{len(categorical_columns)}"
    )

    print(
        f"Numerical features: "
        f"{len(numerical_columns)}"
    )

    numerical_pipeline = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(
                    strategy="median"
                )
            ),
            (
                "scaler",
                StandardScaler()
            ),
        ]
    )

    categorical_pipeline = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(
                    strategy="most_frequent"
                )
            ),
            (
                "encoder",
                OneHotEncoder(
                    handle_unknown="ignore"
                )
            ),
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            (
                "numeric",
                numerical_pipeline,
                numerical_columns
            ),
            (
                "categorical",
                categorical_pipeline,
                categorical_columns
            ),
        ]
    )

    model = LogisticRegression(
        max_iter=2000,
        class_weight="balanced",
        random_state=42
    )

    pipeline = Pipeline(
        steps=[
            (
                "preprocessor",
                preprocessor
            ),
            (
                "model",
                model
            ),
        ]
    )

    return pipeline


# ============================================================
# EVALUATION
# ============================================================

def evaluate_model(
    pipeline,
    X_test,
    y_test
):

    print(
        "\n========== MODEL EVALUATION =========="
    )

    predictions = pipeline.predict(
        X_test
    )

    probabilities = (
        pipeline
        .predict_proba(X_test)[:, 1]
    )

    accuracy = accuracy_score(
        y_test,
        predictions
    )

    precision = precision_score(
        y_test,
        predictions,
        zero_division=0
    )

    recall = recall_score(
        y_test,
        predictions,
        zero_division=0
    )

    f1 = f1_score(
        y_test,
        predictions,
        zero_division=0
    )

    roc_auc = roc_auc_score(
        y_test,
        probabilities
    )

    pr_auc = average_precision_score(
        y_test,
        probabilities
    )

    print(
        f"\nAccuracy : {accuracy:.4f}"
    )

    print(
        f"Precision: {precision:.4f}"
    )

    print(
        f"Recall   : {recall:.4f}"
    )

    print(
        f"F1 Score : {f1:.4f}"
    )

    print(
        f"ROC-AUC  : {roc_auc:.4f}"
    )

    print(
        f"PR-AUC   : {pr_auc:.4f}"
    )

    print("\nConfusion Matrix:")

    cm = confusion_matrix(
        y_test,
        predictions
    )

    print(cm)

    print(
        "\nClassification Report:"
    )

    print(
        classification_report(
            y_test,
            predictions,
            target_names=[
                "Loss",
                "Win"
            ],
            zero_division=0
        )
    )

    return {
        "accuracy": float(accuracy),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "roc_auc": float(roc_auc),
        "pr_auc": float(pr_auc),
        "confusion_matrix": cm.tolist(),
        "test_records": int(len(y_test)),
        "test_wins": int(y_test.sum()),
        "test_losses": int(
            (y_test == 0).sum()
        ),
    }


# ============================================================
# SAVE METRICS
# ============================================================

def save_metrics(metrics):

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            metrics,
            file,
            indent=4
        )

    print(
        "\nSaved temporal validation metrics:"
    )

    print(
        OUTPUT_FILE
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "\n========== TRADEMIND AI ==========\n"
    )

    print(
        "Starting temporal ML validation..."
    )

    df = load_dataset()

    (
        df,
        X,
        y,
        feature_columns
    ) = prepare_data(df)

    print(
        "\nFeatures used:"
    )

    for feature in feature_columns:
        print(
            f"- {feature}"
        )

    (
        X_train,
        X_test,
        y_train,
        y_test
    ) = temporal_split(
        df,
        X,
        y
    )

    pipeline = build_pipeline(
        X_train
    )

    print(
        "\n========== MODEL TRAINING =========="
    )

    print(
        "Training Logistic Regression..."
    )

    pipeline.fit(
        X_train,
        y_train
    )

    print(
        "Training complete."
    )

    metrics = evaluate_model(
        pipeline,
        X_test,
        y_test
    )

    save_metrics(
        metrics
    )

    print(
        "\n===================================="
    )

    print(
        "TEMPORAL VALIDATION COMPLETE"
    )

    print(
        "====================================\n"
    )


if __name__ == "__main__":
    main()