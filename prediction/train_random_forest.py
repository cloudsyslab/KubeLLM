"""Train a leakage-aware Random Forest on KubeLLM response features."""

import argparse
import json
from pathlib import Path
from typing import Dict, List
import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_selection import SelectFromModel
from sklearn.impute import SimpleImputer
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import (
    StratifiedGroupKFold,
    cross_val_predict,
    cross_validate,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler


# These features exist before the debug model executes the proposed plan.
# Outcome fields, durations, and debug token counts are intentionally excluded.
NUMERIC_FEATURES = [
    "response_length",
    "response_word_count",
    "num_code_blocks",
    "num_step_lines",
    "num_command_keywords",
    "num_sentence_tokens",
    "contains_verify",
    "contains_wait",
    "contains_logs",
    "contains_apply",
    "contains_sed",
    "contains_env",
    "contains_selector",
    "contains_probe",
    "contains_docker_build"
]
CATEGORICAL_FEATURES = ["debug_model"]
TARGET_COLUMN = "label_success"
GROUP_COLUMN = "test_name"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Train either success classification or total-runtime regression. "
            "Runtime mode uses log scaling, normalization, RF feature selection, "
            "and training-only outlier removal."
        )
    )
    parser.add_argument(
        "--task",
        choices=["success", "runtime"],
        default="success",
        help="Training target: success classification or runtime regression",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/all_models_features.csv"),
        help="Feature CSV (default: data/all_models_features.csv)",
    )
    parser.add_argument(
        "--model-output",
        type=Path,
        default=Path("data/random_forest.joblib"),
        help="Saved model artifact (default: data/random_forest.joblib)",
    )
    parser.add_argument(
        "--metrics-output",
        type=Path,
        default=Path("data/random_forest_metrics.json"),
        help="Cross-validation metrics JSON",
    )
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--trees", type=int, default=500)
    parser.add_argument(
        "--max-depth",
        type=int,
        help="Tree depth (default: success=6, runtime=8)",
    )
    parser.add_argument(
        "--min-samples-leaf",
        type=int,
        help="Minimum leaf size (default: success=5, runtime=2)",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--selected-features",
        type=int,
        default=8,
        help=(
            "Number of transformed features retained by RF importance; "
            "use 0 to disable selection (default: 8)"
        ),
    )
    parser.add_argument(
        "--selector-trees",
        type=int,
        default=300,
        help="Trees used by the RF feature selector (default: 300)",
    )
    parser.add_argument(
        "--no-normalize",
        action="store_true",
        help="Disable StandardScaler for success classification (ablation only)",
    )
    parser.add_argument(
        "--no-log-scale",
        action="store_true",
        help="Disable log1p scaling for success-classification numeric features",
    )
    parser.add_argument(
        "--exclude-debug-model",
        action="store_true",
        help="Do not use model identity as a predictor (ablation experiment)",
    )
    parser.add_argument(
        "--debug-model",
        help="Exact debug_model required by --task runtime",
    )
    parser.add_argument(
        "--test-cases",
        nargs="+",
        metavar="CASE",
        help="Runtime mode: complete test_name groups to hold out",
    )
    parser.add_argument(
        "--train-fraction",
        type=float,
        help="Runtime mode: fraction of complete test cases used for training",
    )
    parser.add_argument(
        "--runtime-output-dir",
        type=Path,
        default=Path("data/runtime_prediction"),
        help="Runtime-mode output directory",
    )
    parser.add_argument(
        "--outlier-iqr-multiplier",
        type=float,
        default=1.5,
        help="Runtime mode: log-duration IQR outlier fence; 0 disables removal",
    )
    parser.add_argument(
        "--accuracy-tolerance-percent",
        type=float,
        default=20.0,
        help=(
            "Runtime mode: duration is counted accurate within this percentage "
            "of actual time (default: 20)"
        ),
    )
    return parser.parse_args()


def load_labeled_data(
    input_path: Path, categorical_features: List[str]
) -> tuple[pd.DataFrame, pd.Series, pd.Series, pd.DataFrame]:
    if not input_path.is_file():
        raise FileNotFoundError(f"Feature CSV does not exist: {input_path}")
    frame = pd.read_csv(input_path)
    required = set(NUMERIC_FEATURES + categorical_features)
    required.update({TARGET_COLUMN, GROUP_COLUMN})
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"Feature CSV is missing columns: {', '.join(missing)}")
    # ERROR runs have no objective ground-truth label. They must not silently
    # become negative training examples.
    labeled = frame.dropna(subset=[TARGET_COLUMN]).copy()
    labeled[TARGET_COLUMN] = labeled[TARGET_COLUMN].astype(int)
    unexpected_labels = sorted(set(labeled[TARGET_COLUMN]).difference({0, 1}))
    if unexpected_labels:
        raise ValueError(f"Expected binary labels 0/1, found: {unexpected_labels}")
    if labeled[TARGET_COLUMN].nunique() != 2:
        raise ValueError("Training data must contain both success and failure labels")
    for column in NUMERIC_FEATURES:
        original = labeled[column]
        numeric = pd.to_numeric(original, errors="coerce")
        if (original.notna() & numeric.isna()).any():
            raise ValueError(f"Numeric feature {column!r} contains non-numeric values")
        labeled[column] = numeric
    feature_columns = categorical_features + NUMERIC_FEATURES
    return (
        labeled[feature_columns],
        labeled[TARGET_COLUMN],
        labeled[GROUP_COLUMN],
        labeled,
    )


def build_pipeline(
    categorical_features: List[str],
    trees: int,
    max_depth: int,
    min_samples_leaf: int,
    seed: int,
    selected_features: int | None = None,
    selector_trees: int = 300,
    normalize: bool = False,
    log_scale: bool = False,
) -> Pipeline:
    """Build a pipeline whose learned transforms remain inside each CV fold."""
    numeric_transformer: object = SimpleImputer(strategy="median")
    if log_scale or normalize:
        numeric_steps = [("imputer", SimpleImputer(strategy="median"))]
        if log_scale:
            numeric_steps.append(
                (
                    "log1p",
                    FunctionTransformer(np.log1p, feature_names_out="one-to-one"),
                )
            )
        if normalize:
            numeric_steps.append(("scaler", StandardScaler()))
        numeric_transformer = Pipeline(numeric_steps)

    transformers = [
        (
            "numeric",
            numeric_transformer,
            NUMERIC_FEATURES,
        )
    ]
    if categorical_features:
        transformers.append(
            (
                "categorical",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                categorical_features,
            )
        )

    preprocessor = ColumnTransformer(transformers=transformers, remainder="drop")
    steps = [("preprocessor", preprocessor)]
    if selected_features is not None:
        selector_estimator = RandomForestClassifier(
            n_estimators=selector_trees,
            max_depth=max_depth,
            min_samples_leaf=min_samples_leaf,
            max_features="sqrt",
            class_weight="balanced_subsample",
            random_state=seed,
            n_jobs=-1,
        )
        steps.append(
            (
                "feature_selector",
                SelectFromModel(
                    estimator=selector_estimator,
                    threshold=-np.inf,
                    max_features=selected_features,
                ),
            )
        )

    classifier = RandomForestClassifier(
        n_estimators=trees,
        max_depth=max_depth,
        min_samples_leaf=min_samples_leaf,
        max_features="sqrt",
        class_weight="balanced_subsample",
        random_state=seed,
        n_jobs=-1,
    )
    steps.append(("classifier", classifier))
    return Pipeline(steps)


def run_runtime_task(args: argparse.Namespace) -> int:
    """Delegate runtime regression while keeping one public training command."""
    if not args.debug_model:
        raise ValueError("--debug-model is required when --task runtime")
    split_count = int(args.test_cases is not None) + int(
        args.train_fraction is not None
    )
    if split_count != 1:
        raise ValueError(
            "--task runtime requires exactly one of --test-cases or "
            "--train-fraction"
        )

    # Import lazily so existing classification imports and artifacts remain
    # backward compatible. Runtime artifacts intentionally stay separate from
    # success-classification artifacts because their targets are different.
    from train_runtime_predictor import run_runtime_experiment

    runtime_args = argparse.Namespace(
        input=args.input,
        debug_model=args.debug_model,
        test_cases=args.test_cases,
        train_fraction=args.train_fraction,
        output_dir=args.runtime_output_dir,
        selected_features=args.selected_features,
        selector_trees=args.selector_trees,
        trees=args.trees,
        max_depth=args.max_depth if args.max_depth is not None else 8,
        min_samples_leaf=(
            args.min_samples_leaf if args.min_samples_leaf is not None else 2
        ),
        outlier_iqr_multiplier=args.outlier_iqr_multiplier,
        accuracy_tolerance_percent=args.accuracy_tolerance_percent,
        seed=args.seed,
    )
    return run_runtime_experiment(runtime_args)


def summarize_scores(scores: Dict[str, np.ndarray]) -> Dict[str, Dict[str, object]]:
    summary: Dict[str, Dict[str, object]] = {}
    for key, values in scores.items():
        if not key.startswith("test_"):
            continue
        metric_name = key.removeprefix("test_")
        summary[metric_name] = {
            "mean": round(float(np.mean(values)), 4),
            "std": round(float(np.std(values)), 4),
            "folds": [round(float(value), 4) for value in values],
        }
    return summary


def fitted_feature_metadata(pipeline: Pipeline) -> Dict[str, object]:
    """Return auditable transformed/selected feature names and importances."""
    preprocessor = pipeline.named_steps["preprocessor"]
    transformed_names = preprocessor.get_feature_names_out().astype(str).tolist()
    selector = pipeline.named_steps.get("feature_selector")

    if selector is None:
        selected_names = transformed_names
        selection_importances = None
    else:
        support = selector.get_support()
        selected_names = np.asarray(transformed_names, dtype=object)[support].tolist()
        selection_importances = {
            name: float(importance)
            for name, importance in zip(
                transformed_names, selector.estimator_.feature_importances_
            )
        }

    classifier = pipeline.named_steps["classifier"]
    classifier_importances = {
        name: float(importance)
        for name, importance in zip(selected_names, classifier.feature_importances_)
    }
    return {
        "transformed_feature_names": transformed_names,
        "selected_feature_names": selected_names,
        "selection_importances": selection_importances,
        "classifier_importances": classifier_importances,
    }


def main() -> int:
    args = parse_args()
    if args.task == "runtime":
        return run_runtime_task(args)

    if args.max_depth is None:
        args.max_depth = 6
    if args.min_samples_leaf is None:
        args.min_samples_leaf = 5
    if args.folds < 2:
        raise ValueError("--folds must be at least 2")
    if args.trees < 1 or args.max_depth < 1 or args.min_samples_leaf < 1:
        raise ValueError("Tree parameters must be positive integers")
    if args.selector_trees < 1:
        raise ValueError("--selector-trees must be a positive integer")
    if args.selected_features < 0:
        raise ValueError("--selected-features must be non-negative")

    categorical_features = [] if args.exclude_debug_model else CATEGORICAL_FEATURES
    features, labels, groups, labeled_frame = load_labeled_data(
        args.input, categorical_features
    )
    numeric_values = features[NUMERIC_FEATURES].to_numpy(dtype=float)
    if np.isinf(numeric_values).any():
        raise ValueError("Numeric features contain positive or negative infinity")
    if not args.no_log_scale and features[NUMERIC_FEATURES].lt(0.0).any(axis=None):
        negative_columns = features[NUMERIC_FEATURES].columns[
            features[NUMERIC_FEATURES].lt(0.0).any()
        ].tolist()
        raise ValueError(
            "log1p numeric features must be non-negative; found negatives in: "
            + ", ".join(negative_columns)
        )
    max_candidate_features = len(NUMERIC_FEATURES) + sum(
        int(labeled_frame[column].nunique()) for column in categorical_features
    )
    selected_features = args.selected_features or None
    if selected_features is not None and selected_features > max_candidate_features:
        raise ValueError(
            f"--selected-features={selected_features} exceeds the "
            f"{max_candidate_features} transformed candidate features"
        )

    unique_groups = groups.nunique()
    if args.folds > unique_groups:
        raise ValueError(
            f"--folds={args.folds} exceeds the {unique_groups} unique test groups"
        )

    pipeline = build_pipeline(
        categorical_features,
        trees=args.trees,
        max_depth=args.max_depth,
        min_samples_leaf=args.min_samples_leaf,
        seed=args.seed,
        selected_features=selected_features,
        selector_trees=args.selector_trees,
        normalize=not args.no_normalize,
        log_scale=not args.no_log_scale,
    )
    cross_validator = StratifiedGroupKFold(
        n_splits=args.folds,
        shuffle=True,
        random_state=args.seed,
    )
    splits = list(cross_validator.split(features, labels, groups))
    scoring = {
        "accuracy": "accuracy",
        "balanced_accuracy": "balanced_accuracy",
        "f1": "f1",
        "roc_auc": "roc_auc",
        "average_precision": "average_precision",
    }
    scores = cross_validate(
        pipeline,
        features,
        labels,
        cv=splits,
        scoring=scoring,
        n_jobs=1,
    )
    predictions = cross_val_predict(
        pipeline,
        features,
        labels,
        cv=splits,
        method="predict",
        n_jobs=1,
    )

    score_summary = summarize_scores(scores)
    matrix = confusion_matrix(labels, predictions).tolist()
    report = classification_report(labels, predictions, output_dict=True)
    majority_baseline = max(float(labels.mean()), 1.0 - float(labels.mean()))

    print(f"Input rows: {len(pd.read_csv(args.input))}")
    print(f"Labeled rows used: {len(labeled_frame)}")
    print(f"Unique test groups: {unique_groups}")
    print(
        "Labels: "
        f"PASS={int((labels == 1).sum())} FAIL={int((labels == 0).sum())}"
    )
    print(f"Always-majority accuracy baseline: {majority_baseline:.4f}")
    print("\nGrouped cross-validation (unseen test cases):")
    for metric_name, values in score_summary.items():
        print(f"  {metric_name}: {values['mean']:.4f} +/- {values['std']:.4f}")
    print(f"\nOut-of-fold confusion matrix [[TN, FP], [FN, TP]]: {matrix}")
    print(classification_report(labels, predictions, digits=3))

    # Evaluation above never mixes the same test case across train/test folds.
    # Refit on every labeled row to create the final reusable artifact.
    pipeline.fit(features, labels)
    feature_columns = categorical_features + NUMERIC_FEATURES
    feature_metadata = fitted_feature_metadata(pipeline)
    normalization_metadata = {
        "enabled": not args.no_normalize,
        "method": "StandardScaler after median imputation on numeric features",
    }
    log_scaling_metadata = {
        "enabled": not args.no_log_scale,
        "method": "log1p after median imputation on numeric features",
    }
    selection_metadata = {
        "enabled": selected_features is not None,
        "method": "top-k SelectFromModel with RandomForestClassifier importance",
        "selected_features_requested": selected_features,
        "selector_trees": args.selector_trees if selected_features is not None else None,
    }
    artifact = {
        "artifact_schema_version": 2,
        "task": "success_classification",
        "pipeline": pipeline,
        "feature_columns": feature_columns,
        "numeric_features": NUMERIC_FEATURES,
        "categorical_features": categorical_features,
        "target": TARGET_COLUMN,
        "label_definition": "1=ground-truth PASS, 0=ground-truth FAIL",
        "normalization": normalization_metadata,
        "log_scaling": log_scaling_metadata,
        "feature_selection": selection_metadata,
        **feature_metadata,
        "training_rows": len(labeled_frame),
        "test_groups": unique_groups,
        "scikit_learn_version": sklearn.__version__,
        "random_seed": args.seed,
        "cv_metrics": score_summary,
    }
    args.model_output.parent.mkdir(parents=True, exist_ok=True)
    args.metrics_output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, args.model_output)

    metrics_payload = {
        "task": "success_classification",
        "input": str(args.input),
        "model_output": str(args.model_output),
        "rows": len(labeled_frame),
        "label_counts": {
            "success": int((labels == 1).sum()),
            "failure": int((labels == 0).sum()),
        },
        "unique_test_groups": unique_groups,
        "majority_baseline_accuracy": round(majority_baseline, 4),
        "cv_metrics": score_summary,
        "confusion_matrix": matrix,
        "classification_report": report,
        "feature_columns": feature_columns,
        "normalization": normalization_metadata,
        "log_scaling": log_scaling_metadata,
        "feature_selection": selection_metadata,
        **feature_metadata,
    }
    args.metrics_output.write_text(
        json.dumps(metrics_payload, indent=2) + "\n", encoding="utf-8"
    )
    print("Selected features: " + ", ".join(feature_metadata["selected_feature_names"]))
    print(f"Saved final model: {args.model_output}")
    print(f"Saved metrics: {args.metrics_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
