"""Train a leakage-aware model that predicts total KubeLLM run time.

The predictor uses only knowledge-response features that are available before
the debug agent executes. Complete ``test_name`` groups are held out together.
All learned preprocessing, feature selection, and outlier decisions use the
training side of the split only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import time
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import RandomForestRegressor
from sklearn.feature_selection import SelectFromModel
from sklearn.impute import SimpleImputer
from sklearn.compose import TransformedTargetRegressor
from sklearn.metrics import (
    mean_absolute_error,
    mean_absolute_percentage_error,
    mean_squared_log_error,
    median_absolute_error,
    r2_score,
    root_mean_squared_error,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler

from train_random_forest import NUMERIC_FEATURES


MODEL_COLUMN = "debug_model"
GROUP_COLUMN = "test_name"
TARGET_COLUMN = "duration_s"
BENCHMARK_VERSION = 1
PREDICTION_SEMANTICS = (
    "Predicted total end-to-end run duration after the knowledge response "
    "features are available. This is not remaining time."
)
METADATA_COLUMNS = [
    "dataset",
    "iteration",
    "test_name",
    "source_dir",
    "run_status",
    "debug_model",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Predict total KubeLLM run duration for one debug model using "
            "training-only outlier removal, log transforms, normalization, "
            "and Random-Forest feature selection."
        )
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/all_7_models_features.csv"),
        help="Feature CSV containing duration_s (default: data/all_7_models_features.csv)",
    )
    parser.add_argument(
        "--debug-model",
        required=True,
        help="Exact debug_model value to train, for example qwen3.8:27b",
    )
    split_group = parser.add_mutually_exclusive_group(required=True)
    split_group.add_argument(
        "--test-cases",
        nargs="+",
        metavar="CASE",
        help="Complete test_name groups to hold out",
    )
    split_group.add_argument(
        "--train-fraction",
        type=float,
        help="Fraction of complete test_name groups used for training",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/runtime_prediction"),
        help="Parent directory for model, predictions, metrics, and diagnostics",
    )
    parser.add_argument(
        "--selected-features",
        type=int,
        default=8,
        help="Number of features retained by the RF selector (default: 8)",
    )
    parser.add_argument(
        "--selector-trees",
        type=int,
        default=300,
        help="Trees used by the RF feature selector (default: 300)",
    )
    parser.add_argument(
        "--trees",
        type=int,
        default=500,
        help="Trees used by the final RF regressor (default: 500)",
    )
    parser.add_argument("--max-depth", type=int, default=8)
    parser.add_argument("--min-samples-leaf", type=int, default=2)
    parser.add_argument(
        "--outlier-iqr-multiplier",
        type=float,
        default=1.5,
        help=(
            "Remove training durations outside this log-duration IQR fence; "
            "use 0 to disable (default: 1.5)"
        ),
    )
    parser.add_argument(
        "--accuracy-tolerance-percent",
        type=float,
        default=20.0,
        help=(
            "Report accuracy as the share of duration predictions within this "
            "percentage of actual duration (default: 20)"
        ),
    )
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if args.test_cases is not None:
        if len(args.test_cases) != len(set(args.test_cases)):
            raise ValueError("--test-cases cannot contain duplicate names")
    if args.train_fraction is not None:
        if not np.isfinite(args.train_fraction) or not 0.0 < args.train_fraction < 1.0:
            raise ValueError("--train-fraction must be finite and between 0 and 1")
    if not 1 <= args.selected_features <= len(NUMERIC_FEATURES):
        raise ValueError(
            f"--selected-features must be between 1 and {len(NUMERIC_FEATURES)}"
        )
    if args.selector_trees < 1 or args.trees < 1:
        raise ValueError("--selector-trees and --trees must be positive")
    if args.max_depth < 1 or args.min_samples_leaf < 1:
        raise ValueError("--max-depth and --min-samples-leaf must be positive")
    if (
        not np.isfinite(args.outlier_iqr_multiplier)
        or args.outlier_iqr_multiplier < 0.0
    ):
        raise ValueError("--outlier-iqr-multiplier must be finite and non-negative")
    if (
        not np.isfinite(args.accuracy_tolerance_percent)
        or args.accuracy_tolerance_percent < 0.0
    ):
        raise ValueError(
            "--accuracy-tolerance-percent must be finite and non-negative"
        )


def safe_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").lower()
    return slug or "model"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as input_file:
        for chunk in iter(lambda: input_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_selected_model(input_path: Path, debug_model: str) -> pd.DataFrame:
    if not input_path.is_file():
        raise FileNotFoundError(f"Feature CSV does not exist: {input_path}")

    frame = pd.read_csv(input_path)
    required = set(NUMERIC_FEATURES + [MODEL_COLUMN, GROUP_COLUMN, TARGET_COLUMN])
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"Feature CSV is missing columns: {', '.join(missing)}")

    available_models = sorted(frame[MODEL_COLUMN].dropna().astype(str).unique())
    selected = frame.loc[frame[MODEL_COLUMN] == debug_model].copy()
    if selected.empty:
        choices = ", ".join(available_models) or "none"
        raise ValueError(
            f"No rows found for debug model {debug_model!r}. Available values: {choices}"
        )
    if selected[GROUP_COLUMN].isna().any():
        raise ValueError("Selected rows contain a missing test_name")
    if selected[GROUP_COLUMN].nunique() < 2:
        raise ValueError("At least two unique test_name groups are required")

    for column in NUMERIC_FEATURES + [TARGET_COLUMN]:
        selected[column] = pd.to_numeric(selected[column], errors="coerce")

    feature_values = selected[NUMERIC_FEATURES].to_numpy(dtype=float)
    if np.isinf(feature_values).any():
        raise ValueError("Predictor features contain positive or negative infinity")
    if selected[NUMERIC_FEATURES].lt(0).any(axis=None):
        negative_columns = selected[NUMERIC_FEATURES].columns[
            selected[NUMERIC_FEATURES].lt(0).any()
        ].tolist()
        raise ValueError(
            "log1p predictor features must be non-negative; found negatives in: "
            + ", ".join(negative_columns)
        )

    target = selected[TARGET_COLUMN].to_numpy(dtype=float)
    invalid_target = np.isinf(target) | (np.isfinite(target) & (target < 0.0))
    if invalid_target.any():
        invalid_count = int(invalid_target.sum())
        raise ValueError(
            f"{TARGET_COLUMN} contains {invalid_count} negative or infinite "
            "value(s); durations must be missing, zero, or finite and non-negative"
        )
    selected["duration_available"] = np.isfinite(target) & (target > 0.0)
    return selected


def split_case_groups(
    selected: pd.DataFrame,
    test_cases: Iterable[str] | None,
    train_fraction: float | None,
    seed: int,
) -> Tuple[pd.DataFrame, pd.DataFrame, list[str], list[str], str]:
    # CLI case names are strings. Normalize the source column before both
    # membership validation and masking so numeric-looking case identifiers
    # cannot silently produce an empty held-out set.
    selected = selected.copy()
    selected[GROUP_COLUMN] = selected[GROUP_COLUMN].astype(str)
    available_cases = sorted(selected[GROUP_COLUMN].unique())

    if test_cases is not None:
        held_out = [str(case_name) for case_name in test_cases]
        unknown = sorted(set(held_out).difference(available_cases))
        if unknown:
            raise ValueError(
                "Unknown held-out test case(s): "
                + ", ".join(unknown)
                + ". Available values: "
                + ", ".join(available_cases)
            )
        if not held_out or len(held_out) >= len(available_cases):
            raise ValueError("--test-cases must leave at least one training case")
        split_method = "explicit_test_cases"
    else:
        if train_fraction is None:
            raise ValueError("A split method is required")
        training_count = int(len(available_cases) * train_fraction)
        if training_count < 1 or training_count >= len(available_cases):
            raise ValueError(
                "--train-fraction must leave at least one complete case on each side"
            )
        _, automatic_test_cases = train_test_split(
            available_cases,
            train_size=train_fraction,
            random_state=seed,
            shuffle=True,
        )
        held_out = list(automatic_test_cases)
        split_method = "seeded_random_test_case_groups"

    test_mask = selected[GROUP_COLUMN].isin(held_out)
    train_all = selected.loc[~test_mask].copy()
    test_all = selected.loc[test_mask].copy()
    train_names = sorted(train_all[GROUP_COLUMN].astype(str).unique())
    test_names = sorted(test_all[GROUP_COLUMN].astype(str).unique())

    overlap = sorted(set(train_names).intersection(test_names))
    if overlap:
        raise ValueError(f"Train/test group leakage detected: {', '.join(overlap)}")
    if sorted(train_names + test_names) != available_cases:
        raise ValueError("The group split did not cover every available test case")
    return train_all, test_all, train_names, test_names, split_method


def remove_training_outliers(
    train: pd.DataFrame, multiplier: float
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """Remove target outliers using fences learned only from training rows."""
    usable = train.loc[train["duration_available"]].copy()
    excluded_invalid = int(len(train) - len(usable))
    if usable.empty:
        raise ValueError("No positive finite training durations are available")

    log_duration = np.log1p(usable[TARGET_COLUMN].to_numpy(dtype=float))
    q1, q3 = np.quantile(log_duration, [0.25, 0.75])
    iqr = float(q3 - q1)

    if multiplier == 0.0:
        lower_log = float("-inf")
        upper_log = float("inf")
        inlier_mask = np.ones(len(usable), dtype=bool)
    else:
        lower_log = float(q1 - multiplier * iqr)
        upper_log = float(q3 + multiplier * iqr)
        inlier_mask = (log_duration >= lower_log) & (log_duration <= upper_log)

    filtered = usable.loc[inlier_mask].copy()
    removed = usable.loc[~inlier_mask].copy()
    removed["log1p_duration_s"] = log_duration[~inlier_mask]
    if len(filtered) < 2:
        raise ValueError(
            "Outlier removal left fewer than two training rows; reduce the IQR "
            "strictness or use --outlier-iqr-multiplier 0"
        )

    info: Dict[str, Any] = {
        "method": "log1p_duration_tukey_iqr" if multiplier else "disabled",
        "iqr_multiplier": float(multiplier),
        "q1_log1p_seconds": float(q1),
        "q3_log1p_seconds": float(q3),
        "iqr_log1p_seconds": iqr,
        "lower_log1p_seconds": None if not np.isfinite(lower_log) else lower_log,
        "upper_log1p_seconds": None if not np.isfinite(upper_log) else upper_log,
        "lower_seconds": (
            None if not np.isfinite(lower_log) else max(0.0, float(np.expm1(lower_log)))
        ),
        "upper_seconds": (
            None if not np.isfinite(upper_log) else float(np.expm1(upper_log))
        ),
        "training_rows_before": int(len(train)),
        "training_rows_with_valid_duration": int(len(usable)),
        "invalid_or_nonpositive_training_rows_excluded": excluded_invalid,
        "outlier_rows_removed": int(len(removed)),
        "training_rows_after": int(len(filtered)),
        "removed_test_cases": sorted(removed[GROUP_COLUMN].astype(str).unique()),
    }
    return filtered, removed, info


def build_runtime_model(args: argparse.Namespace) -> TransformedTargetRegressor:
    preprocessing = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(strategy="median", keep_empty_features=True),
            ),
            (
                "log1p_features",
                FunctionTransformer(np.log1p, feature_names_out="one-to-one"),
            ),
            ("normalizer", StandardScaler()),
        ]
    )
    selector_estimator = RandomForestRegressor(
        n_estimators=args.selector_trees,
        max_depth=args.max_depth,
        min_samples_leaf=args.min_samples_leaf,
        max_features="sqrt",
        random_state=args.seed,
        n_jobs=-1,
    )
    selector = SelectFromModel(
        estimator=selector_estimator,
        threshold=-np.inf,
        max_features=args.selected_features,
    )
    final_estimator = RandomForestRegressor(
        n_estimators=args.trees,
        max_depth=args.max_depth,
        min_samples_leaf=args.min_samples_leaf,
        max_features="sqrt",
        random_state=args.seed,
        n_jobs=-1,
    )
    feature_pipeline = Pipeline(
        steps=[
            ("preprocessor", preprocessing),
            ("selector", selector),
            ("regressor", final_estimator),
        ]
    )
    return TransformedTargetRegressor(
        regressor=feature_pipeline,
        func=np.log1p,
        inverse_func=np.expm1,
        check_inverse=True,
    )


def selected_feature_table(
    fitted_model: TransformedTargetRegressor,
) -> Tuple[list[str], pd.DataFrame]:
    fitted_pipeline = fitted_model.regressor_
    selector = fitted_pipeline.named_steps["selector"]
    support = selector.get_support()
    selected_names = np.asarray(NUMERIC_FEATURES, dtype=object)[support].tolist()
    selector_importance = selector.estimator_.feature_importances_
    final_importance = fitted_pipeline.named_steps["regressor"].feature_importances_
    final_by_name = dict(zip(selected_names, final_importance))

    table = pd.DataFrame(
        {
            "feature": NUMERIC_FEATURES,
            "rf_selection_importance": selector_importance,
            "selected": support,
            "final_rf_importance": [
                final_by_name.get(feature, np.nan) for feature in NUMERIC_FEATURES
            ],
        }
    )
    table = table.sort_values(
        ["selected", "rf_selection_importance"], ascending=[False, False]
    ).reset_index(drop=True)
    return selected_names, table


def evaluate_runtime_predictions(
    actual: np.ndarray,
    predicted: np.ndarray,
    training_median_seconds: float,
    accuracy_tolerance_percent: float,
) -> Dict[str, Any]:
    if len(actual) == 0:
        raise ValueError("No positive finite held-out durations are available for scoring")
    baseline = np.full(len(actual), training_median_seconds, dtype=float)
    relative_error = np.abs(actual - predicted) / actual
    within_tolerance = relative_error <= accuracy_tolerance_percent / 100.0
    target_has_variance = bool(len(actual) >= 2 and not np.allclose(actual, actual[0]))
    return {
        "scored_rows": int(len(actual)),
        "mae_seconds": float(mean_absolute_error(actual, predicted)),
        "median_absolute_error_seconds": float(
            median_absolute_error(actual, predicted)
        ),
        "rmse_seconds": float(root_mean_squared_error(actual, predicted)),
        "mape_percent": float(
            100.0 * mean_absolute_percentage_error(actual, predicted)
        ),
        "accuracy_tolerance_percent": float(accuracy_tolerance_percent),
        "within_tolerance_accuracy": float(np.mean(within_tolerance)),
        "within_tolerance_accuracy_percent": float(100.0 * np.mean(within_tolerance)),
        "rmsle": float(
            np.sqrt(mean_squared_log_error(actual, np.maximum(predicted, 0.0)))
        ),
        "r2": float(r2_score(actual, predicted)) if target_has_variance else None,
        "mean_actual_seconds": float(np.mean(actual)),
        "mean_predicted_seconds": float(np.mean(predicted)),
        "total_actual_seconds": float(np.sum(actual)),
        "total_predicted_seconds": float(np.sum(predicted)),
        "total_actual_minutes": float(np.sum(actual) / 60.0),
        "total_predicted_minutes": float(np.sum(predicted) / 60.0),
        "training_median_baseline_seconds": float(training_median_seconds),
        "baseline_mae_seconds": float(mean_absolute_error(actual, baseline)),
        "baseline_rmse_seconds": float(root_mean_squared_error(actual, baseline)),
        "r2_note": (
            None
            if target_has_variance
            else "R2 is null because the held-out target has no measurable variance."
        ),
    }


def build_prediction_frame(
    test_all: pd.DataFrame,
    predicted_seconds: np.ndarray,
    outlier_info: Dict[str, Any],
) -> pd.DataFrame:
    columns = [column for column in METADATA_COLUMNS if column in test_all.columns]
    output = test_all[columns].copy()
    actual = pd.to_numeric(test_all[TARGET_COLUMN], errors="coerce")
    actual_values = actual.to_numpy(dtype=float)
    scored = np.isfinite(actual_values) & (actual_values > 0.0)

    output["actual_total_duration_s"] = actual
    output["actual_total_duration_minutes"] = actual / 60.0
    output["predicted_total_duration_s"] = predicted_seconds
    output["predicted_total_duration_minutes"] = predicted_seconds / 60.0
    output["scored"] = scored
    absolute_error = np.full(len(output), np.nan, dtype=float)
    absolute_percentage_error = np.full(len(output), np.nan, dtype=float)
    absolute_error[scored] = np.abs(
        actual_values[scored] - predicted_seconds[scored]
    )
    absolute_percentage_error[scored] = (
        100.0 * absolute_error[scored] / actual_values[scored]
    )
    output["absolute_error_s"] = absolute_error
    output["absolute_percentage_error"] = absolute_percentage_error

    outside = pd.Series(pd.NA, index=output.index, dtype="boolean")
    lower = outlier_info["lower_log1p_seconds"]
    upper = outlier_info["upper_log1p_seconds"]
    if lower is not None and upper is not None:
        log_actual = np.log1p(actual.loc[scored])
        outside.loc[scored] = (log_actual < lower) | (log_actual > upper)
    output["actual_outside_training_outlier_fence"] = outside

    sort_columns = [GROUP_COLUMN]
    if "iteration" in output.columns:
        sort_columns.append("iteration")
    return output.sort_values(sort_columns).reset_index(drop=True)


def _versions() -> Dict[str, str]:
    return {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "scikit_learn": sklearn.__version__,
        "joblib": joblib.__version__,
    }


def run_runtime_experiment(args: argparse.Namespace) -> int:
    """Train/evaluate runtime regression from an already parsed configuration."""
    validate_args(args)
    selected = load_selected_model(args.input, args.debug_model)
    train_all, test_all, train_names, test_names, split_method = split_case_groups(
        selected,
        test_cases=args.test_cases,
        train_fraction=args.train_fraction,
        seed=args.seed,
    )
    train, removed_outliers, outlier_info = remove_training_outliers(
        train_all, args.outlier_iqr_multiplier
    )

    model = build_runtime_model(args)
    fit_started = time.perf_counter()
    model.fit(train[NUMERIC_FEATURES], train[TARGET_COLUMN])
    fit_seconds = time.perf_counter() - fit_started

    predict_started = time.perf_counter()
    predicted_all = np.maximum(
        model.predict(test_all[NUMERIC_FEATURES]).astype(float), 0.0
    )
    predict_seconds = time.perf_counter() - predict_started
    if not np.isfinite(predicted_all).all():
        raise ValueError("The fitted model produced a non-finite duration prediction")

    selected_features, importance_table = selected_feature_table(model)
    prediction_frame = build_prediction_frame(test_all, predicted_all, outlier_info)
    scored_positions = np.flatnonzero(prediction_frame["scored"].to_numpy(dtype=bool))
    actual_scored = prediction_frame.loc[
        prediction_frame["scored"], "actual_total_duration_s"
    ].to_numpy(dtype=float)
    predicted_scored = prediction_frame.loc[
        prediction_frame["scored"], "predicted_total_duration_s"
    ].to_numpy(dtype=float)
    if len(scored_positions) != len(actual_scored):
        raise ValueError("Internal prediction alignment error")

    training_median = float(train[TARGET_COLUMN].median())
    evaluation = evaluate_runtime_predictions(
        actual_scored,
        predicted_scored,
        training_median,
        args.accuracy_tolerance_percent,
    )

    input_hash = sha256_file(args.input)
    training_script_hash = sha256_file(Path(__file__).resolve())
    versions = _versions()
    configuration = {
        "benchmark_version": BENCHMARK_VERSION,
        "input_sha256": input_hash,
        "training_script_sha256": training_script_hash,
        "scikit_learn_version": versions["scikit_learn"],
        "debug_model": args.debug_model,
        "split_method": split_method,
        "train_cases": train_names,
        "test_cases": test_names,
        "train_fraction": args.train_fraction,
        "selected_features_requested": args.selected_features,
        "selector_trees": args.selector_trees,
        "trees": args.trees,
        "max_depth": args.max_depth,
        "min_samples_leaf": args.min_samples_leaf,
        "outlier_iqr_multiplier": args.outlier_iqr_multiplier,
        "accuracy_tolerance_percent": args.accuracy_tolerance_percent,
        "seed": args.seed,
    }
    run_id = hashlib.sha256(
        json.dumps(configuration, sort_keys=True).encode("utf-8")
    ).hexdigest()[:10]
    slug = safe_slug(args.debug_model)
    split_suffix = f"train{len(train_names)}_test{len(test_names)}"
    run_dir = args.output_dir / f"{slug}_{split_suffix}_{run_id}"
    run_dir.mkdir(parents=True, exist_ok=True)

    model_path = run_dir / f"runtime_model_{slug}_{split_suffix}.joblib"
    predictions_path = run_dir / f"runtime_predictions_{slug}_{split_suffix}.csv"
    metrics_path = run_dir / f"runtime_metrics_{slug}_{split_suffix}.json"
    importance_path = run_dir / f"feature_importance_{slug}_{split_suffix}.csv"
    outliers_path = run_dir / f"removed_training_outliers_{slug}_{split_suffix}.csv"

    artifact = {
        "artifact_schema_version": 2,
        "task": "runtime_regression",
        "model": model,
        "feature_columns": list(NUMERIC_FEATURES),
        "selected_features": selected_features,
        "target": TARGET_COLUMN,
        "target_transform": "log1p during fit; expm1 during predict",
        "feature_transform": "median imputation -> log1p -> StandardScaler",
        "feature_selection": "top-k RandomForestRegressor importance",
        "prediction_semantics": PREDICTION_SEMANTICS,
        "debug_model": args.debug_model,
        "train_cases": train_names,
        "test_cases": test_names,
        "outlier_info": outlier_info,
        "configuration": configuration,
        "run_id": run_id,
        "versions": versions,
    }
    joblib.dump(artifact, model_path)
    prediction_frame.to_csv(predictions_path, index=False)
    importance_table.to_csv(importance_path, index=False)

    outlier_columns = [
        column
        for column in METADATA_COLUMNS + [TARGET_COLUMN, "log1p_duration_s"]
        if column in removed_outliers.columns
    ]
    removed_outliers[outlier_columns].to_csv(outliers_path, index=False)

    metrics_payload = {
        "benchmark_version": BENCHMARK_VERSION,
        "task": "runtime_regression",
        "run_id": run_id,
        "input": str(args.input),
        "input_sha256": input_hash,
        "training_script_sha256": training_script_hash,
        "debug_model": args.debug_model,
        "prediction_semantics": PREDICTION_SEMANTICS,
        "split_method": split_method,
        "train_cases": train_names,
        "test_cases": test_names,
        "train_case_count": len(train_names),
        "test_case_count": len(test_names),
        "train_rows_before_outlier_removal": int(len(train_all)),
        "train_rows_used": int(len(train)),
        "test_rows_predicted": int(len(test_all)),
        "test_rows_scored": int(prediction_frame["scored"].sum()),
        "test_rows_unscored": int((~prediction_frame["scored"]).sum()),
        "outlier_removal": outlier_info,
        "candidate_features": list(NUMERIC_FEATURES),
        "selected_features": selected_features,
        "evaluation": evaluation,
        "fit_seconds": float(fit_seconds),
        "predict_seconds": float(predict_seconds),
        "configuration": configuration,
        "versions": versions,
        "paths": {
            "model": str(model_path),
            "predictions": str(predictions_path),
            "feature_importance": str(importance_path),
            "removed_training_outliers": str(outliers_path),
        },
    }
    metrics_path.write_text(
        json.dumps(metrics_payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )

    print(f"Debug model: {args.debug_model}")
    print(
        f"Cases: {len(train_names)} train / {len(test_names)} test; "
        f"rows used: {len(train)} train / {len(actual_scored)} scored test"
    )
    print(
        f"Training outliers removed: {outlier_info['outlier_rows_removed']} "
        f"(test rows were not removed)"
    )
    print("Selected features: " + ", ".join(selected_features))
    print(
        f"MAE: {evaluation['mae_seconds']:.2f}s | "
        f"RMSE: {evaluation['rmse_seconds']:.2f}s | "
        f"MAPE: {evaluation['mape_percent']:.2f}% | "
        f"R2: {evaluation['r2'] if evaluation['r2'] is not None else 'N/A'}"
    )
    print(
        f"Accuracy within +/-{evaluation['accuracy_tolerance_percent']:.0f}%: "
        f"{evaluation['within_tolerance_accuracy_percent']:.2f}%"
    )
    print(
        f"Held-out predicted total: {evaluation['total_predicted_minutes']:.2f} min | "
        f"actual: {evaluation['total_actual_minutes']:.2f} min"
    )
    print(f"Model: {model_path}")
    print(f"Predictions: {predictions_path}")
    print(f"Metrics: {metrics_path}")
    return 0


def main() -> int:
    return run_runtime_experiment(parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
