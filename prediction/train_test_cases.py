"""Train one debug model with a group-safe test-case holdout.

All iterations of a test case stay on the same side of the split. Runs whose
ground-truth status is ERROR have no binary label, so they receive predictions
but are excluded from training and evaluation metrics.
"""

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_absolute_percentage_error,
    precision_score,
    recall_score,
    r2_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split

from train_random_forest import NUMERIC_FEATURES, build_pipeline


MODEL_COLUMN = "debug_model"
GROUP_COLUMN = "test_name"
TARGET_COLUMN = "label_success"
EXPECTED_CASES = 27


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Train a Random Forest for one debug model while keeping every "
            "iteration of a test case entirely in training or testing."
        )
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/all_models_features.csv"),
        help="Combined feature CSV (default: data/all_models_features.csv)",
    )
    parser.add_argument(
        "--debug-model",
        required=True,
        help="Exact debug_model value to select, for example qwen3.8:27b",
    )
    split_group = parser.add_mutually_exclusive_group(required=True)
    split_group.add_argument(
        "--test-cases",
        nargs="+",
        metavar="CASE",
        help="Explicit test_name values to hold out from training",
    )
    split_group.add_argument(
        "--train-fraction",
        type=float,
        help=(
            "Fraction of complete test-case groups used for training; for "
            "example, 0.9 selects 24 of 27 groups for training"
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/case_holdout"),
        help="Directory for the model, predictions, and metrics",
    )
    parser.add_argument("--trees", type=int, default=500)
    parser.add_argument("--max-depth", type=int, default=6)
    parser.add_argument("--min-samples-leaf", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def safe_slug(value: str) -> str:
    """Convert a model name into a portable filename component."""
    slug = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").lower()
    return slug or "model"


def label_counts(labels: pd.Series) -> Dict[str, int]:
    return {
        "success": int((labels == 1).sum()),
        "failure": int((labels == 0).sum()),
    }


def evaluate_predictions(
    labels: pd.Series,
    predictions: np.ndarray,
    success_scores: np.ndarray,
    training_majority_class: int,
) -> Dict[str, Any]:
    both_classes = bool(labels.nunique() == 2)
    has_zero_target = bool((labels == 0).any())
    majority_predictions = np.full(
        len(labels), training_majority_class, dtype=int
    )

    metrics: Dict[str, Any] = {
        "accuracy": float(accuracy_score(labels, predictions)),
        "balanced_accuracy": (
            float(balanced_accuracy_score(labels, predictions))
            if both_classes
            else None
        ),
        "precision": float(precision_score(labels, predictions, zero_division=0)),
        "recall": float(recall_score(labels, predictions, zero_division=0)),
        "f1": float(f1_score(labels, predictions, zero_division=0)),
        "roc_auc": (
            float(roc_auc_score(labels, success_scores)) if both_classes else None
        ),
        "average_precision": (
            float(average_precision_score(labels, success_scores))
            if both_classes
            else None
        ),
        # These regression-style metrics compare the binary outcome (0/1) with
        # the predicted probability of success, not with the hard class label.
        "mae_on_probabilities": float(
            mean_absolute_error(labels, success_scores)
        ),
        "mape_on_probabilities": (
            float(mean_absolute_percentage_error(labels, success_scores))
            if not has_zero_target
            else None
        ),
        "r2_on_probabilities": (
            float(r2_score(labels, success_scores, force_finite=False))
            if both_classes
            else None
        ),
        "regression_metric_basis": (
            "actual label_success (0/1) versus predicted success probability"
        ),
        "majority_baseline_class": training_majority_class,
        "majority_baseline_accuracy": float(
            accuracy_score(labels, majority_predictions)
        ),
        "confusion_matrix": confusion_matrix(
            labels, predictions, labels=[0, 1]
        ).tolist(),
        "classification_report": classification_report(
            labels,
            predictions,
            labels=[0, 1],
            target_names=["FAIL", "PASS"],
            output_dict=True,
            zero_division=0,
        ),
        "test_contains_both_classes": both_classes,
    }
    if not both_classes:
        metrics["metric_note"] = (
            "Balanced accuracy, ROC-AUC, and average precision are null because "
            "the labeled held-out rows contain only one class. R2 is also null "
            "because the target has no variance."
        )
    if has_zero_target:
        metrics["mape_note"] = (
            "Standard MAPE is null because label_success contains zero, making "
            "percentage error undefined."
        )
    return metrics


def validate_parameters(args: argparse.Namespace) -> None:
    if args.test_cases is not None:
        if len(set(args.test_cases)) != len(args.test_cases):
            raise ValueError("--test-cases cannot contain duplicate case names")
        if not 1 <= len(args.test_cases) < EXPECTED_CASES:
            raise ValueError(
                f"--test-cases must contain between 1 and {EXPECTED_CASES - 1} "
                "case names"
            )
    if args.train_fraction is not None:
        if not np.isfinite(args.train_fraction):
            raise ValueError("--train-fraction must be a finite number")
        if not 0.0 < args.train_fraction < 1.0:
            raise ValueError("--train-fraction must be greater than 0 and less than 1")
        training_case_count = int(EXPECTED_CASES * args.train_fraction)
        if training_case_count < 1 or training_case_count >= EXPECTED_CASES:
            raise ValueError(
                "--train-fraction must leave at least one complete case in both "
                "training and testing"
            )
    if args.trees < 1 or args.max_depth < 1 or args.min_samples_leaf < 1:
        raise ValueError("Tree parameters must be positive integers")


def load_selected_model(args: argparse.Namespace) -> pd.DataFrame:
    if not args.input.is_file():
        raise FileNotFoundError(f"Feature CSV does not exist: {args.input}")

    frame = pd.read_csv(args.input)
    required = set(NUMERIC_FEATURES)
    required.update({MODEL_COLUMN, GROUP_COLUMN, TARGET_COLUMN})
    missing_columns = sorted(required.difference(frame.columns))
    if missing_columns:
        raise ValueError(
            f"Feature CSV is missing columns: {', '.join(missing_columns)}"
        )

    available_models = sorted(frame[MODEL_COLUMN].dropna().astype(str).unique())
    selected = frame.loc[frame[MODEL_COLUMN] == args.debug_model].copy()
    if selected.empty:
        choices = ", ".join(available_models) or "none"
        raise ValueError(
            f"No rows found for debug model {args.debug_model!r}. "
            f"Available values: {choices}"
        )
    if selected[GROUP_COLUMN].isna().any():
        raise ValueError("Selected rows contain a missing test_name")

    available_cases = sorted(selected[GROUP_COLUMN].astype(str).unique())
    if len(available_cases) != EXPECTED_CASES:
        raise ValueError(
            f"Expected {EXPECTED_CASES} unique test cases for {args.debug_model!r}, "
            f"but found {len(available_cases)}"
        )
    if args.test_cases is not None:
        unknown_cases = sorted(set(args.test_cases).difference(available_cases))
        if unknown_cases:
            raise ValueError(
                "Unknown held-out test case(s): "
                f"{', '.join(unknown_cases)}. Available values: "
                f"{', '.join(available_cases)}"
            )
    return selected


def main() -> int:
    args = parse_args()
    validate_parameters(args)
    selected = load_selected_model(args)

    # Select complete scenario groups first. Dropping ERROR rows beforehand could
    # hide a scenario or put iterations of one scenario on both sides.
    available_names = sorted(selected[GROUP_COLUMN].astype(str).unique())
    if args.test_cases is not None:
        held_out_names = list(args.test_cases)
        split_method = "explicit_test_cases"
    else:
        _, automatically_held_out = train_test_split(
            available_names,
            train_size=args.train_fraction,
            random_state=args.seed,
            shuffle=True,
        )
        held_out_names = list(automatically_held_out)
        split_method = "seeded_random_test_case_groups"

    test_mask = selected[GROUP_COLUMN].isin(held_out_names)
    train_all = selected.loc[~test_mask].copy()
    test_all = selected.loc[test_mask].copy()
    train_names = sorted(train_all[GROUP_COLUMN].astype(str).unique())
    actual_test_names = sorted(test_all[GROUP_COLUMN].astype(str).unique())
    expected_test_count = len(set(held_out_names))
    expected_train_count = EXPECTED_CASES - expected_test_count
    if len(train_names) != expected_train_count:
        raise ValueError(
            f"Expected {expected_train_count} training test cases, but found "
            f"{len(train_names)}"
        )
    if len(actual_test_names) != expected_test_count:
        raise ValueError(
            f"Expected {expected_test_count} held-out test cases, but found "
            f"{len(actual_test_names)}"
        )
    if set(train_names).intersection(actual_test_names):
        raise RuntimeError("A test case appears in both training and test data")

    train = train_all.dropna(subset=[TARGET_COLUMN]).copy()
    test = test_all.dropna(subset=[TARGET_COLUMN]).copy()
    if train.empty:
        raise ValueError("No labeled training rows remain after excluding ERROR runs")
    if test.empty:
        raise ValueError("The held-out cases have no labeled rows to evaluate")
    unexpected_labels = sorted(
        set(train[TARGET_COLUMN]).union(test[TARGET_COLUMN]).difference({0, 1})
    )
    if unexpected_labels:
        raise ValueError(f"Expected binary labels 0/1, found: {unexpected_labels}")
    train[TARGET_COLUMN] = train[TARGET_COLUMN].astype(int)
    test[TARGET_COLUMN] = test[TARGET_COLUMN].astype(int)
    if train[TARGET_COLUMN].nunique() != 2:
        raise ValueError("The training cases must contain both PASS and FAIL labels")

    pipeline = build_pipeline(
        categorical_features=[],
        trees=args.trees,
        max_depth=args.max_depth,
        min_samples_leaf=args.min_samples_leaf,
        seed=args.seed,
    )
    pipeline.fit(train[NUMERIC_FEATURES], train[TARGET_COLUMN])

    class_values = pipeline.named_steps["classifier"].classes_
    success_class_indexes = np.flatnonzero(class_values == 1)
    if len(success_class_indexes) != 1:
        raise RuntimeError(
            f"Expected classifier classes to contain label 1, found {class_values}"
        )
    success_class_index = int(success_class_indexes[0])
    labeled_predictions = pipeline.predict(test[NUMERIC_FEATURES]).astype(int)
    labeled_scores = pipeline.predict_proba(test[NUMERIC_FEATURES])[
        :, success_class_index
    ]
    evaluation = evaluate_predictions(
        test[TARGET_COLUMN],
        labeled_predictions,
        labeled_scores,
        training_majority_class=int(train[TARGET_COLUMN].mean() >= 0.5),
    )

    # Preserve ERROR/unlabeled held-out runs in the prediction CSV so it is clear
    # which rows were predicted but excluded from objective scoring.
    all_predictions = pipeline.predict(test_all[NUMERIC_FEATURES]).astype(int)
    all_scores = pipeline.predict_proba(test_all[NUMERIC_FEATURES])[
        :, success_class_index
    ]
    preferred_metadata = [
        "dataset",
        "iteration",
        MODEL_COLUMN,
        GROUP_COLUMN,
        "run_status",
        TARGET_COLUMN,
    ]
    metadata_columns = [
        column for column in preferred_metadata if column in test_all.columns
    ]
    prediction_frame = test_all[metadata_columns].copy()
    prediction_frame["predicted_success"] = all_predictions
    prediction_frame["success_score"] = all_scores
    prediction_frame["scored"] = prediction_frame[TARGET_COLUMN].notna()
    prediction_frame["correct"] = pd.Series(
        pd.NA, index=prediction_frame.index, dtype="boolean"
    )
    scored_mask = prediction_frame["scored"]
    prediction_frame.loc[scored_mask, "correct"] = (
        prediction_frame.loc[scored_mask, "predicted_success"].astype(int)
        == prediction_frame.loc[scored_mask, TARGET_COLUMN].astype(int)
    )
    prediction_frame = prediction_frame.sort_values(
        [GROUP_COLUMN] + (["iteration"] if "iteration" in prediction_frame else [])
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    model_slug = safe_slug(args.debug_model)
    suffix = f"{model_slug}_train{len(train_names)}_test{len(actual_test_names)}"
    if args.train_fraction is not None:
        suffix = f"{suffix}_seed{args.seed}"
    model_path = args.output_dir / f"random_forest_{suffix}.joblib"
    predictions_path = args.output_dir / f"predictions_{suffix}.csv"
    metrics_path = args.output_dir / f"metrics_{suffix}.json"

    artifact = {
        "pipeline": pipeline,
        "feature_columns": list(NUMERIC_FEATURES),
        "numeric_features": list(NUMERIC_FEATURES),
        "categorical_features": [],
        "debug_model": args.debug_model,
        "split_method": split_method,
        "requested_train_fraction": args.train_fraction,
        "actual_train_case_fraction": len(train_names) / EXPECTED_CASES,
        "train_cases": train_names,
        "test_cases": actual_test_names,
        "target": TARGET_COLUMN,
        "label_definition": "1=ground-truth PASS, 0=ground-truth FAIL",
        "training_labeled_rows": len(train),
        "scikit_learn_version": sklearn.__version__,
        "random_seed": args.seed,
    }
    joblib.dump(artifact, model_path)
    prediction_frame.to_csv(predictions_path, index=False)

    per_case: Dict[str, Dict[str, Any]] = {}
    for case_name, case_rows in test_all.groupby(GROUP_COLUMN, sort=True):
        case_labeled = case_rows.dropna(subset=[TARGET_COLUMN])
        per_case[str(case_name)] = {
            "raw_rows": len(case_rows),
            "labeled_rows": len(case_labeled),
            "unscored_error_rows": int(case_rows[TARGET_COLUMN].isna().sum()),
            "label_counts": label_counts(case_labeled[TARGET_COLUMN]),
        }

    metrics_payload = {
        "input": str(args.input),
        "debug_model": args.debug_model,
        "split_unit": GROUP_COLUMN,
        "split_method": split_method,
        "requested_train_fraction": args.train_fraction,
        "actual_train_case_fraction": len(train_names) / EXPECTED_CASES,
        "actual_test_case_fraction": len(actual_test_names) / EXPECTED_CASES,
        "train_cases": train_names,
        "test_cases": actual_test_names,
        "case_counts": {
            "total": EXPECTED_CASES,
            "train": len(train_names),
            "test": len(actual_test_names),
        },
        "row_counts": {
            "train_raw": len(train_all),
            "train_labeled": len(train),
            "train_unscored_errors": int(train_all[TARGET_COLUMN].isna().sum()),
            "test_raw": len(test_all),
            "test_labeled": len(test),
            "test_unscored_errors": int(test_all[TARGET_COLUMN].isna().sum()),
        },
        "train_label_counts": label_counts(train[TARGET_COLUMN]),
        "test_label_counts": label_counts(test[TARGET_COLUMN]),
        "test_case_summary": per_case,
        "metrics_on_labeled_test_rows": evaluation,
        "feature_columns": list(NUMERIC_FEATURES),
        "model_output": str(model_path),
        "predictions_output": str(predictions_path),
        "parameters": {
            "trees": args.trees,
            "max_depth": args.max_depth,
            "min_samples_leaf": args.min_samples_leaf,
            "seed": args.seed,
        },
    }
    metrics_path.write_text(
        json.dumps(metrics_payload, indent=2) + "\n", encoding="utf-8"
    )

    counts = metrics_payload["row_counts"]
    test_labels = metrics_payload["test_label_counts"]
    print(f"Debug model: {args.debug_model}")
    print(f"Split method: {split_method}")
    if args.train_fraction is not None:
        print(f"Requested training fraction: {args.train_fraction:.1%}")
        print(
            "Actual case split: "
            f"{len(train_names) / EXPECTED_CASES:.1%} train / "
            f"{len(actual_test_names) / EXPECTED_CASES:.1%} test"
        )
    print(f"Train cases: {len(train_names)}")
    print(f"Held-out cases: {', '.join(actual_test_names)}")
    print(
        "Train rows: "
        f"{counts['train_raw']} raw, {counts['train_labeled']} labeled, "
        f"{counts['train_unscored_errors']} ERROR/unscored"
    )
    print(
        "Test rows: "
        f"{counts['test_raw']} raw, {counts['test_labeled']} scored, "
        f"{counts['test_unscored_errors']} ERROR/unscored"
    )
    print(
        "Test labels: "
        f"PASS={test_labels['success']} FAIL={test_labels['failure']}"
    )
    print(f"Accuracy: {evaluation['accuracy']:.4f}")
    print(f"F1: {evaluation['f1']:.4f}")
    print(
        "MAE (0/1 outcome vs success probability): "
        f"{evaluation['mae_on_probabilities']:.4f}"
    )
    if evaluation["mape_on_probabilities"] is not None:
        print(f"MAPE: {evaluation['mape_on_probabilities'] * 100.0:.2f}%")
    else:
        print("MAPE: N/A (actual FAIL labels are zero)")
    if evaluation["r2_on_probabilities"] is not None:
        print(
            "R2 (0/1 outcome vs success probability): "
            f"{evaluation['r2_on_probabilities']:.4f}"
        )
    else:
        print("R2: N/A (held-out labels contain one class)")
    if evaluation["roc_auc"] is not None:
        print(f"ROC-AUC: {evaluation['roc_auc']:.4f}")
    else:
        print("ROC-AUC: N/A (held-out labels contain one class)")
    print(f"Confusion matrix [[TN, FP], [FN, TP]]: {evaluation['confusion_matrix']}")
    print(f"Saved model: {model_path}")
    print(f"Saved predictions: {predictions_path}")
    print(f"Saved metrics: {metrics_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
