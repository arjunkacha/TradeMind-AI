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
# TRADEMIND AI - ML TRAINING ENGINE
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[3]

INPUT_FILE = BASE_DIR / "data" / "ml_dataset.csv"

MODEL_DIR = BASE_DIR / "models"
MODEL_FILE = MODEL_DIR / "trade_outcome_model.joblib"
METRICS_FILE = MODEL_DIR / "training_metrics.json"
FEATURE_FILE = MODEL_DIR / "model_features.json"


# ============================================================
# CONFIGURATION
# ============================================================

TEST_SIZE = 0.20
RANDOM_STATE = 42


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

    print(
        "\nPreparing training data..."
    )

    df = df.copy()

    # --------------------------------------------------------
    # Convert time
    # --------------------------------------------------------

    df["entry_time"] = pd.to_datetime(
        df["entry_time"],
        errors="coerce"
    )

    # --------------------------------------------------------
    # Sort chronologically
    # --------------------------------------------------------

    df = df.sort_values(
        "entry_time"
    ).reset_index(drop=True)

    # --------------------------------------------------------
    # Target
    # --------------------------------------------------------

    if "target" not in df.columns:

        raise ValueError(
            "Target column not found in ML dataset."
        )

    y = df["target"].astype(int)

    # --------------------------------------------------------
    # Remove identifiers and future/unusable fields
    # --------------------------------------------------------

    drop_columns = [
        "target",
        "trade_id",
        "account",
        "entry_time",
    ]

    existing_drop_columns = [
        column
        for column in drop_columns
        if column in df.columns
    ]

    X = df.drop(
        columns=existing_drop_columns
    )

    # --------------------------------------------------------
    # Remove duplicate columns
    # --------------------------------------------------------

    X = X.loc[
        :,
        ~X.columns.duplicated()
    ]

    print(
        f"Training features: {len(X.columns)}"
    )

    print(
        "\nFeatures:"
    )

    for column in X.columns:
        print(f"- {column}")

    return X, y


# ============================================================
# CHRONOLOGICAL TRAIN / TEST SPLIT
# ============================================================

def chronological_split(X, y):

    split_index = int(
        len(X) * (1 - TEST_SIZE)
    )

    X_train = X.iloc[
        :split_index
    ].copy()

    X_test = X.iloc[
        split_index:
    ].copy()

    y_train = y.iloc[
        :split_index
    ].copy()

    y_test = y.iloc[
        split_index:
    ].copy()

    print(
        "\n========== DATA SPLIT =========="
    )

    print(
        f"Training records: {len(X_train):,}"
    )

    print(
        f"Testing records : {len(X_test):,}"
    )

    print(
        "\nTraining target distribution:"
    )

    print(
        y_train.value_counts()
    )

    print(
        "\nTesting target distribution:"
    )

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

def build_preprocessor(X):

    categorical_columns = X.select_dtypes(
        include=["object"]
    ).columns.tolist()

    numerical_columns = [
        column
        for column in X.columns
        if column not in categorical_columns
    ]

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

    preprocessor = ColumnTransformer(
        transformers=[
            (
                "categorical",
                categorical_pipeline,
                categorical_columns
            ),
            (
                "numerical",
                numerical_pipeline,
                numerical_columns
            ),
        ]
    )

    return preprocessor


# ============================================================
# BUILD MODEL
# ============================================================

def build_model(preprocessor):

    model = LogisticRegression(
        max_iter=2000,
        class_weight="balanced",
        random_state=RANDOM_STATE
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
# TRAIN
# ============================================================

def train_model(
    pipeline,
    X_train,
    y_train
):

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

    return pipeline


# ============================================================
# EVALUATION
# ============================================================

def evaluate_model(
    model,
    X_test,
    y_test
):

    print(
        "\n========== MODEL EVALUATION =========="
    )

    predictions = model.predict(
        X_test
    )

    probabilities = model.predict_proba(
        X_test
    )[:, 1]

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

    try:

        roc_auc = roc_auc_score(
            y_test,
            probabilities
        )

    except ValueError:

        roc_auc = None

    try:

        pr_auc = average_precision_score(
            y_test,
            probabilities
        )

    except ValueError:

        pr_auc = None

    cm = confusion_matrix(
        y_test,
        predictions
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

    if roc_auc is not None:

        print(
            f"ROC-AUC  : {roc_auc:.4f}"
        )

    if pr_auc is not None:

        print(
            f"PR-AUC   : {pr_auc:.4f}"
        )

    print(
        "\nConfusion Matrix:"
    )

    print(
        cm
    )

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

    metrics = {
        "accuracy": float(accuracy),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "roc_auc": (
            float(roc_auc)
            if roc_auc is not None
            else None
        ),
        "pr_auc": (
            float(pr_auc)
            if pr_auc is not None
            else None
        ),
        "test_records": int(len(y_test)),
        "test_wins": int(
            (y_test == 1).sum()
        ),
        "test_losses": int(
            (y_test == 0).sum()
        ),
        "confusion_matrix": cm.tolist(),
    }

    return metrics


# ============================================================
# SAVE MODEL
# ============================================================

def save_model(
    model,
    X,
    metrics
):

    MODEL_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    joblib.dump(
        model,
        MODEL_FILE
    )

    with open(
        METRICS_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            metrics,
            file,
            indent=4
        )

    feature_metadata = {
        "feature_count": len(X.columns),
        "features": X.columns.tolist()
    }

    with open(
        FEATURE_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            feature_metadata,
            file,
            indent=4
        )

    print(
        "\n========== MODEL SAVED =========="
    )

    print(
        f"Model:"
    )

    print(
        MODEL_FILE
    )

    print(
        "\nMetrics:"
    )

    print(
        METRICS_FILE
    )

    print(
        "\nFeature metadata:"
    )

    print(
        FEATURE_FILE
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "\n========== TRADEMIND AI ==========\n"
    )

    print(
        "Starting ML training..."
    )

    # --------------------------------------------------------
    # Load
    # --------------------------------------------------------

    df = load_dataset()

    # --------------------------------------------------------
    # Prepare
    # --------------------------------------------------------

    X, y = prepare_data(
        df
    )

    # --------------------------------------------------------
    # Chronological split
    # --------------------------------------------------------

    (
        X_train,
        X_test,
        y_train,
        y_test
    ) = chronological_split(
        X,
        y
    )

    # --------------------------------------------------------
    # Preprocessor
    # --------------------------------------------------------

    preprocessor = build_preprocessor(
        X_train
    )

    # --------------------------------------------------------
    # Model
    # --------------------------------------------------------

    model = build_model(
        preprocessor
    )

    # --------------------------------------------------------
    # Train
    # --------------------------------------------------------

    model = train_model(
        model,
        X_train,
        y_train
    )

    # --------------------------------------------------------
    # Evaluate
    # --------------------------------------------------------

    metrics = evaluate_model(
        model,
        X_test,
        y_test
    )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    save_model(
        model,
        X,
        metrics
    )

    print(
        "\n=================================="
    )

    print(
        "ML TRAINING COMPLETE"
    )

    print(
        "==================================\n"
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
