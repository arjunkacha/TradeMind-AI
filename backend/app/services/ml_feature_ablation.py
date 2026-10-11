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
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


# ============================================================
# TRADEMIND AI - ML FEATURE ABLATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[3]

INPUT_FILE = BASE_DIR / "data" / "ml_dataset.csv"
OUTPUT_FILE = (
    BASE_DIR
    / "models"
    / "feature_ablation"
    / "ablation_results.json"
)

TARGET = "target"
TEST_SIZE = 0.20


# ============================================================
# FEATURE GROUPS
# ============================================================

FEATURE_GROUPS = {

    "A_Context_Only": [
        "symbol",
        "direction",
        "entry_hour",
        "entry_minute",
        "day_of_week_num",
    ],

    "B_Trading_Behavior": [
        "trades_today",
        "time_since_previous_trade",
        "previous_position_size",
        "position_size_change_pct",
        "average_position_size",
        "position_size_ratio",
    ],

    "C_Previous_Outcome": [
        "previous_trade_pnl",
        "previous_trade_is_loss",
        "previous_trade_is_win",
        "previous_loss_streak",
        "previous_session_pnl",
    ],

    "D_Behavior_Detectors": [
        "behavior_overtrading",
        "behavior_rapid_reentry",
        "behavior_oversizing",
    ],
}


# ============================================================
# LOAD DATA
# ============================================================

def load_data():

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"ML dataset not found: {INPUT_FILE}"
        )

    df = pd.read_csv(INPUT_FILE)

    print(
        f"Loaded records: {len(df):,}"
    )

    df["entry_time"] = pd.to_datetime(
        df["entry_time"],
        errors="coerce"
    )

    if df["entry_time"].isna().any():
        raise ValueError(
            "Invalid entry_time values detected."
        )

    # Always chronological.
    df = (
        df.sort_values("entry_time")
        .reset_index(drop=True)
    )

    return df


# ============================================================
# BUILD FEATURE SETS
# ============================================================

def build_experiments():

    experiments = {}

    # Context only
    experiments["A_Context_Only"] = (
        FEATURE_GROUPS["A_Context_Only"]
    )

    # Context + behavior
    experiments["B_Context_Plus_Behavior"] = (
        FEATURE_GROUPS["A_Context_Only"]
        + FEATURE_GROUPS["B_Trading_Behavior"]
    )

    # Context + previous outcome
    experiments["C_Context_Plus_Previous_Outcome"] = (
        FEATURE_GROUPS["A_Context_Only"]
        + FEATURE_GROUPS["C_Previous_Outcome"]
    )

    # Context + trading behavior + previous outcome
    experiments["D_Context_Behavior_Outcome"] = (
        FEATURE_GROUPS["A_Context_Only"]
        + FEATURE_GROUPS["B_Trading_Behavior"]
        + FEATURE_GROUPS["C_Previous_Outcome"]
    )

    # Full currently trusted feature set
    experiments["E_Full_Trusted"] = (
        FEATURE_GROUPS["A_Context_Only"]
        + FEATURE_GROUPS["B_Trading_Behavior"]
        + FEATURE_GROUPS["C_Previous_Outcome"]
        + FEATURE_GROUPS["D_Behavior_Detectors"]
    )

    return experiments


# ============================================================
# PREPROCESSOR
# ============================================================

def build_pipeline(X):

    categorical_columns = (
        X
        .select_dtypes(
            include=["object", "string"]
        )
        .columns
        .tolist()
    )

    numerical_columns = (
        X
        .select_dtypes(
            include=[np.number]
        )
        .columns
        .tolist()
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

    return Pipeline(
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


# ============================================================
# RUN ONE EXPERIMENT
# ============================================================

def run_experiment(
    name,
    df,
    features
):

    print(
        f"\n{'=' * 60}"
    )

    print(
        f"EXPERIMENT: {name}"
    )

    print(
        f"{'=' * 60}"
    )

    available_features = [
        feature
        for feature in features
        if feature in df.columns
    ]

    missing_features = [
        feature
        for feature in features
        if feature not in df.columns
    ]

    if missing_features:

        print(
            "\nWARNING - Missing features:"
        )

        for feature in missing_features:
            print(
                f"- {feature}"
            )

    print(
        f"\nFeatures: {len(available_features)}"
    )

    for feature in available_features:
        print(
            f"- {feature}"
        )

    X = df[available_features].copy()
    y = df[TARGET].copy()

    split_index = int(
        len(df) * (1 - TEST_SIZE)
    )

    X_train = X.iloc[:split_index]
    X_test = X.iloc[split_index:]

    y_train = y.iloc[:split_index]
    y_test = y.iloc[split_index:]

    pipeline = build_pipeline(
        X_train
    )

    print(
        "\nTraining..."
    )

    pipeline.fit(
        X_train,
        y_train
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

    # IMPORTANT:
    # target 0 = losing trade.
    loss_mask = y_test == 0

    loss_predictions = (
        predictions[loss_mask]
    )

    loss_actual = (
        y_test[loss_mask]
    )

    loss_recall = recall_score(
        loss_actual,
        loss_predictions,
        pos_label=0,
        zero_division=0
    )

    loss_precision = precision_score(
        loss_actual,
        loss_predictions,
        pos_label=0,
        zero_division=0
    )

    print(
        "\nResults:"
    )

    print(
        f"Accuracy       : {accuracy:.4f}"
    )

    print(
        f"Precision      : {precision:.4f}"
    )

    print(
        f"Recall         : {recall:.4f}"
    )

    print(
        f"F1             : {f1:.4f}"
    )

    print(
        f"ROC-AUC        : {roc_auc:.4f}"
    )

    print(
        f"PR-AUC         : {pr_auc:.4f}"
    )

    print(
        f"Loss Precision  : {loss_precision:.4f}"
    )

    print(
        f"Loss Recall     : {loss_recall:.4f}"
    )

    return {
        "experiment": name,
        "feature_count": len(
            available_features
        ),
        "features": available_features,
        "accuracy": float(accuracy),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "roc_auc": float(roc_auc),
        "pr_auc": float(pr_auc),
        "loss_precision": float(
            loss_precision
        ),
        "loss_recall": float(
            loss_recall
        ),
        "train_records": int(
            len(X_train)
        ),
        "test_records": int(
            len(X_test)
        ),
    }


# ============================================================
# SAVE RESULTS
# ============================================================

def save_results(results):

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
            results,
            file,
            indent=4
        )

    print(
        "\nSaved ablation results:"
    )

    print(
        OUTPUT_FILE
    )


# ============================================================
# SUMMARY
# ============================================================

def show_summary(results):

    print(
        "\n\n========== ABLATION SUMMARY ==========\n"
    )

    summary = pd.DataFrame(results)

    display_columns = [
        "experiment",
        "feature_count",
        "accuracy",
        "roc_auc",
        "pr_auc",
        "loss_precision",
        "loss_recall",
    ]

    print(
        summary[
            display_columns
        ]
        .sort_values(
            "roc_auc",
            ascending=False
        )
        .to_string(
            index=False
        )
    )

    print(
        "\n======================================\n"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "\n========== TRADEMIND AI ==========\n"
    )

    print(
        "Starting ML feature ablation..."
    )

    df = load_data()

    experiments = (
        build_experiments()
    )

    results = []

    for name, features in experiments.items():

        result = run_experiment(
            name,
            df,
            features
        )

        results.append(
            result
        )

    save_results(
        results
    )

    show_summary(
        results
    )


if __name__ == "__main__":
    main()