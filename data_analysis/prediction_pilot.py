#!/usr/bin/env python3
"""Audit and evaluate an offline, task-grouped KubeLLM success predictor.

The feature CSV is the pinned Adiba handoff export. It contains numeric
KnowledgeAgent-response features and candidate debug-model identity, but not
raw plans. This script never reads run status, verifier verdict, self-report,
test name, duration, or debug token counts as prediction inputs. Test names are
used only to keep every attempt for a scenario in the same validation fold.

Example:
    python data_analysis/prediction_pilot.py \
      --feature-csv .local/prediction_pilot/adiba_all_7_models_features.csv \
      --canonical-data data \
      --output-dir .local/prediction_pilot/report
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_selection import SelectFromModel
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss, roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, PolynomialFeatures, StandardScaler


HANDOFF_COMMIT = "62b0951c5f47aa0f0bc7297300af9e583095b066"
HANDOFF_CSV_URL = (
    "https://raw.githubusercontent.com/cloudsyslab/KubeLLM/"
    f"{HANDOFF_COMMIT}/data/all_7_models_features.csv"
)
PRICE_SNAPSHOT_DATE = "2026-10-17"
OFFICIAL_TOKEN_PRICES_PER_MILLION = {
    "gpt-5-mini": {"input": 0.25, "output": 2.00},
    "gpt-5-nano": {"input": 0.05, "output": 0.40},
}
OPENAI_PRICE_SOURCES = {
    "gpt-5-mini": "https://developers.openai.com/api/docs/models/gpt-5-mini",
    "gpt-5-nano": "https://developers.openai.com/api/docs/models/gpt-5-nano",
}
RUNPOD_A40_PRICE_SOURCE = "https://www.runpod.io/pricing"
RUNPOD_A40_SECURE_CLOUD_USD_PER_HOUR = 0.59
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
    "contains_docker_build",
]
CATEGORICAL_FEATURES = ["debug_model"]
TARGET = "ground_truth_passed"
GROUP = "test_name"
LOGISTIC_C_GRID = (0.01, 0.1, 1.0, 10.0)
MATCHED_MODELS = (
    "glm-4.7-flash:latest",
    "gpt-5.6-luna",
    "gpt-6-luna",
    "nemotron-cascade-2:30b",
    "oss-20b",
    "qwen3.8:27b",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_feature_data(path: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
    if not path.is_file():
        raise FileNotFoundError(f"Feature CSV not found: {path}")
    all_rows = pd.read_csv(path)
    required = set(NUMERIC_FEATURES + CATEGORICAL_FEATURES + [TARGET, GROUP])
    missing = sorted(required - set(all_rows.columns))
    if missing:
        raise ValueError(f"Feature CSV is missing required columns: {', '.join(missing)}")
    if all_rows.empty:
        raise ValueError("Feature CSV contains no rows")
    if all_rows[GROUP].isna().any() or all_rows["debug_model"].isna().any():
        raise ValueError("test_name and debug_model must be present for every row")

    target = pd.to_numeric(all_rows[TARGET], errors="coerce")
    invalid = target.notna() & ~target.isin((0, 1))
    if invalid.any():
        raise ValueError("ground_truth_passed must contain only true, false, or missing")
    if "label_success" in all_rows:
        source_label = pd.to_numeric(all_rows["label_success"], errors="coerce")
        known = target.notna()
        if (source_label[known].to_numpy() != target[known].to_numpy()).any():
            raise ValueError("label_success disagrees with authoritative ground_truth_passed")
        if source_label.notna().sum() != target.notna().sum():
            raise ValueError("label_success availability disagrees with Ground Truth availability")
    if "label_available" in all_rows:
        available = pd.to_numeric(all_rows["label_available"], errors="coerce")
        if not available.isin((0, 1)).all():
            raise ValueError("label_available must contain only 0 or 1")
        if not np.array_equal(available.astype(bool).to_numpy(), target.notna().to_numpy()):
            raise ValueError("label_available disagrees with Ground Truth availability")

    for feature in NUMERIC_FEATURES:
        original = all_rows[feature]
        numeric = pd.to_numeric(original, errors="coerce")
        if (original.notna() & numeric.isna()).any():
            raise ValueError(f"Numeric feature {feature!r} contains non-numeric values")
        all_rows[feature] = numeric
    all_rows[TARGET] = target
    labeled = all_rows.loc[all_rows[TARGET].notna()].copy()
    if labeled[TARGET].nunique() != 2:
        raise ValueError("Need both Ground Truth successes and failures to train")
    if labeled[GROUP].nunique() < 5:
        raise ValueError("Need at least five distinct task groups for grouped validation")
    features = all_rows[NUMERIC_FEATURES + CATEGORICAL_FEATURES].copy()
    return all_rows.reset_index(drop=True), labeled, features


def grouped_splits(
    y: pd.Series, groups: pd.Series, folds: int, seed: int
) -> list[tuple[np.ndarray, np.ndarray]]:
    count = min(folds, int(groups.nunique()))
    if count < 2:
        raise ValueError("Grouped cross-validation needs at least two task groups")
    splitter = StratifiedGroupKFold(n_splits=count, shuffle=True, random_state=seed)
    return list(splitter.split(np.zeros((len(y), 1)), y, groups))


def preprocessor() -> ColumnTransformer:
    numeric = Pipeline(
        [("imputer", SimpleImputer(strategy="median")), ("scale", StandardScaler())]
    )
    categorical = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    return ColumnTransformer(
        [
            ("numeric", numeric, NUMERIC_FEATURES),
            ("categorical", categorical, CATEGORICAL_FEATURES),
        ],
        sparse_threshold=0,
    )


def logistic_pipeline(c_value: float) -> Pipeline:
    """Regularized logistic model with candidate × response-feature effects."""
    return Pipeline(
        [
            ("preprocessor", preprocessor()),
            (
                "interactions",
                PolynomialFeatures(degree=2, interaction_only=True, include_bias=False),
            ),
            ("classifier", LogisticRegression(C=c_value, max_iter=3000, solver="lbfgs")),
        ]
    )


def adiba_random_forest_pipeline(seed: int) -> Pipeline:
    """Reproduce the handoff RF structure and fixed success-mode parameters."""
    selector = RandomForestClassifier(
        n_estimators=300,
        max_depth=6,
        min_samples_leaf=5,
        max_features="sqrt",
        class_weight="balanced_subsample",
        random_state=seed,
        n_jobs=1,
    )
    classifier = RandomForestClassifier(
        n_estimators=500,
        max_depth=6,
        min_samples_leaf=5,
        max_features="sqrt",
        class_weight="balanced_subsample",
        random_state=seed,
        n_jobs=1,
    )
    return Pipeline(
        [
            ("preprocessor", preprocessor()),
            (
                "feature_selector",
                SelectFromModel(estimator=selector, threshold=-np.inf, max_features=8),
            ),
            ("classifier", classifier),
        ]
    )


def probability_logit(probability: np.ndarray) -> np.ndarray:
    clipped = np.clip(np.asarray(probability, dtype=float), 1e-6, 1 - 1e-6)
    return np.log(clipped / (1 - clipped)).reshape(-1, 1)


def fit_grouped_rf_calibrator(
    x: pd.DataFrame, y: pd.Series, groups: pd.Series, seed: int, folds: int
) -> LogisticRegression:
    """Fit Platt scaling only on RF scores produced out of task-group folds."""
    crossfit_probability = np.full(len(y), np.nan, dtype=float)
    for inner_fold, (train_idx, valid_idx) in enumerate(grouped_splits(y, groups, folds, seed), start=1):
        forest = adiba_random_forest_pipeline(seed + inner_fold)
        forest.fit(x.iloc[train_idx], y.iloc[train_idx].astype(int))
        crossfit_probability[valid_idx] = forest.predict_proba(x.iloc[valid_idx])[:, 1]
    calibrator = LogisticRegression(C=1000.0, max_iter=3000, solver="lbfgs")
    calibrator.fit(probability_logit(crossfit_probability), y.astype(int))
    return calibrator


def apply_rf_calibrator(calibrator: LogisticRegression, raw_probability: np.ndarray) -> np.ndarray:
    return calibrator.predict_proba(probability_logit(raw_probability))[:, 1]


def predict_research_probability(bundle: dict[str, Any], feature_rows: pd.DataFrame) -> np.ndarray:
    """Predict Ground Truth success for new response-feature rows offline."""
    missing = sorted(set(NUMERIC_FEATURES + CATEGORICAL_FEATURES) - set(feature_rows.columns))
    if missing:
        raise ValueError(f"Prediction rows are missing features: {', '.join(missing)}")
    raw = bundle["base_model"].predict_proba(
        feature_rows[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
    )[:, 1]
    return apply_rf_calibrator(bundle["calibrator"], raw)


def choose_logistic_c(
    x: pd.DataFrame, y: pd.Series, groups: pd.Series, seed: int, folds: int
) -> tuple[float, list[dict[str, float]]]:
    inner = grouped_splits(y, groups, min(folds, 4), seed)
    scores: list[dict[str, float]] = []
    for c_value in LOGISTIC_C_GRID:
        squared_errors: list[float] = []
        for train_idx, valid_idx in inner:
            model = logistic_pipeline(c_value)
            model.fit(x.iloc[train_idx], y.iloc[train_idx].astype(int))
            probability = model.predict_proba(x.iloc[valid_idx])[:, 1]
            squared_errors.extend(
                np.square(probability - y.iloc[valid_idx].astype(float).to_numpy()).tolist()
            )
        scores.append({"C": c_value, "inner_brier": float(np.mean(squared_errors))})
    chosen = min(scores, key=lambda row: (row["inner_brier"], row["C"]))
    return float(chosen["C"]), scores


def model_prior_predictions(
    train: pd.DataFrame, test: pd.DataFrame
) -> np.ndarray:
    task_rates = train.groupby([GROUP, "debug_model"], sort=True)[TARGET].mean()
    model_rates = task_rates.groupby(level="debug_model").mean()
    global_rate = float(train[TARGET].mean())
    return test["debug_model"].map(model_rates).fillna(global_rate).to_numpy(dtype=float)


def cluster_bootstrap_brier(
    frame: pd.DataFrame, probability_col: str, seed: int, reps: int
) -> tuple[float, float]:
    valid = frame.dropna(subset=[TARGET])
    grouped = [group for _, group in valid.groupby(GROUP, sort=True)]
    if len(grouped) < 2 or reps < 1:
        return math.nan, math.nan
    rng = np.random.default_rng(seed)
    errors = [
        np.square(g[probability_col].to_numpy() - g[TARGET].astype(float).to_numpy())
        for g in grouped
    ]
    counts = np.array([len(values) for values in errors], dtype=float)
    sums = np.array([values.sum() for values in errors], dtype=float)
    draws = rng.integers(0, len(grouped), size=(reps, len(grouped)))
    estimates = sums[draws].sum(axis=1) / counts[draws].sum(axis=1)
    low, high = np.quantile(estimates, [0.025, 0.975])
    return float(low), float(high)


def score_rows(
    frame: pd.DataFrame,
    predictor: str,
    group_name: str,
    bootstrap_seed: int,
    bootstrap_reps: int,
) -> dict[str, Any]:
    valid = frame.dropna(subset=[TARGET, predictor])
    y = valid[TARGET].astype(int).to_numpy()
    p = np.clip(valid[predictor].to_numpy(dtype=float), 1e-6, 1 - 1e-6)
    brier = float(np.mean(np.square(p - y))) if len(valid) else math.nan
    try:
        auc = float(roc_auc_score(y, p))
    except ValueError:
        auc = math.nan
    lo, hi = cluster_bootstrap_brier(valid, predictor, bootstrap_seed, bootstrap_reps)
    by_task = valid.assign(_success=valid[TARGET].astype(float), _pred=p).groupby(GROUP)
    return {
        "predictor": predictor,
        "scope": group_name,
        "n_attempts_gt_known": int(len(valid)),
        "n_attempts_gt_unknown": int(len(frame) - len(valid)),
        "n_task_scenarios": int(valid[GROUP].nunique()),
        "brier": brier,
        "brier_ci95_low_task_clustered": lo,
        "brier_ci95_high_task_clustered": hi,
        "log_loss": float(log_loss(y, p, labels=[0, 1])) if len(valid) else math.nan,
        "roc_auc_secondary": auc,
        "mean_predicted_probability": float(np.mean(p)) if len(valid) else math.nan,
        "pooled_ground_truth_success_rate": float(np.mean(y)) if len(valid) else math.nan,
        "equal_task_mean_ground_truth_success_rate": float(by_task["_success"].mean().mean()) if len(valid) else math.nan,
        "equal_task_mean_predicted_probability": float(by_task["_pred"].mean().mean()) if len(valid) else math.nan,
    }


def build_metrics(oof: pd.DataFrame, bootstrap_seed: int, bootstrap_reps: int) -> pd.DataFrame:
    predictor_cols = ("p_model_prior", "p_logistic", "p_adiba_rf", "p_adiba_rf_calibrated")
    rows = []
    for index, column in enumerate(predictor_cols):
        rows.append(score_rows(oof, column, "all candidates / pooled attempts", bootstrap_seed + index, bootstrap_reps))
        for model, frame in oof.groupby("debug_model", sort=True):
            rows.append(
                score_rows(
                    frame,
                    column,
                    str(model),
                    bootstrap_seed + index + len(rows),
                    bootstrap_reps,
                )
            )
    return pd.DataFrame(rows)


def calibration_table(oof: pd.DataFrame) -> pd.DataFrame:
    bins = np.linspace(0, 1, 6)
    rows = []
    known = oof.dropna(subset=[TARGET])
    for predictor in ("p_model_prior", "p_logistic", "p_adiba_rf", "p_adiba_rf_calibrated"):
        probability = known[predictor].clip(0, 1)
        bucket = np.minimum(np.digitize(probability, bins[1:-1], right=False), 4)
        work = known.assign(_bin=bucket, _p=probability, _y=known[TARGET].astype(float))
        for bin_index in range(5):
            cell = work[work._bin == bin_index]
            rows.append(
                {
                    "predictor": predictor,
                    "probability_bin": f"[{bins[bin_index]:.1f}, {bins[bin_index + 1]:.1f}{']' if bin_index == 4 else ')'}",
                    "n_attempts": len(cell),
                    "n_task_scenarios": int(cell[GROUP].nunique()),
                    "mean_predicted_probability": float(cell._p.mean()) if len(cell) else math.nan,
                    "observed_ground_truth_success_rate": float(cell._y.mean()) if len(cell) else math.nan,
                }
            )
    return pd.DataFrame(rows)


def workload_table(all_rows: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for model, frame in all_rows.groupby("debug_model", sort=True):
        known = frame.dropna(subset=[TARGET])
        task_rates = known.groupby(GROUP)[TARGET].mean()
        rows.append(
            {
                "debug_model": model,
                "attempts_total": int(len(frame)),
                "attempts_gt_known": int(len(known)),
                "attempts_gt_unknown": int(len(frame) - len(known)),
                "task_scenarios": int(frame[GROUP].nunique()),
                "pooled_attempt_success_rate": float(known[TARGET].mean()) if len(known) else math.nan,
                "equal_task_mean_success_rate": float(task_rates.mean()) if len(task_rates) else math.nan,
                "mean_logged_duration_s": float(pd.to_numeric(frame.get("duration_s"), errors="coerce").mean()) if "duration_s" in frame else math.nan,
                "mean_debug_total_tokens": float(pd.to_numeric(frame.get("debug_total_tokens"), errors="coerce").mean()) if "debug_total_tokens" in frame else math.nan,
            }
        )
    return pd.DataFrame(rows)


def canonical_cost_reference(data_dir: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    # Import the repository parser; resolve its root because iter_run_dirs
    # returns absolute source paths and parse() forms relative configuration names.
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import analyze  # type: ignore[import-not-found]

    parsed, issues = analyze.parse(data_dir.resolve())
    columns = [
        "debug_model",
        "test_case",
        "api_model",
        "verification_model",
        "api_cost",
        "api_input_tokens",
        "api_output_tokens",
        "debug_cost",
        "verification_cost",
        "verification_input_tokens",
        "verification_output_tokens",
        "debug_duration_s",
        "total_cost",
    ]
    if parsed.empty:
        empty_columns = columns + ["api_cost_repriced", "verification_cost_repriced"]
        return pd.DataFrame(columns=empty_columns), {"parsed_rows": 0, "validation_findings": len(issues)}
    costs = parsed[columns].copy()
    for column in ("api_cost", "debug_cost", "verification_cost", "total_cost"):
        costs[column] = pd.to_numeric(costs[column], errors="coerce")
    for column in (
        "api_input_tokens",
        "api_output_tokens",
        "verification_input_tokens",
        "verification_output_tokens",
        "debug_duration_s",
    ):
        costs[column] = pd.to_numeric(costs[column], errors="coerce")
    costs["api_cost_repriced"] = costs.apply(
        lambda row: token_cost(row.api_model, row.api_input_tokens, row.api_output_tokens), axis=1
    )
    costs["verification_cost_repriced"] = costs.apply(
        lambda row: token_cost(
            row.verification_model, row.verification_input_tokens, row.verification_output_tokens
        ),
        axis=1,
    )
    return costs, {
        "parsed_rows": int(len(parsed)),
        "validation_findings": int(len(issues)),
        "validation_errors": int((issues.severity == "error").sum()) if len(issues) else 0,
        "validation_warnings": int((issues.severity == "warning").sum()) if len(issues) else 0,
        "api_models": sorted(parsed.api_model.dropna().astype(str).unique().tolist()),
        "verification_models": sorted(parsed.verification_model.dropna().astype(str).unique().tolist()),
        "price_snapshot_date": PRICE_SNAPSHOT_DATE,
        "official_token_prices_per_million": OFFICIAL_TOKEN_PRICES_PER_MILLION,
        "openai_price_sources": OPENAI_PRICE_SOURCES,
        "a40_secure_cloud_usd_per_hour_reference": RUNPOD_A40_SECURE_CLOUD_USD_PER_HOUR,
        "a40_price_source": RUNPOD_A40_PRICE_SOURCE,
    }


def token_cost(model: Any, input_tokens: Any, output_tokens: Any) -> float:
    """Reprice standard input/output token counts when the model has a fixed rate."""
    prices = OFFICIAL_TOKEN_PRICES_PER_MILLION.get(str(model))
    try:
        input_count = float(input_tokens)
        output_count = float(output_tokens)
    except (TypeError, ValueError):
        return math.nan
    if prices is None or not math.isfinite(input_count + output_count) or min(input_count, output_count) < 0:
        return math.nan
    return (
        input_count * prices["input"] + output_count * prices["output"]
    ) / 1_000_000


def paired_campaign_estimates(costs: pd.DataFrame, repetitions: tuple[int, ...]) -> pd.DataFrame:
    """Scale current-rate API/verifier and logged debug costs for a paired campaign."""
    common = costs[costs.debug_model.isin(MATCHED_MODELS)].copy()
    required = common.dropna(
        subset=["api_cost_repriced", "debug_cost", "verification_cost_repriced"]
    )
    if required.empty:
        return pd.DataFrame()
    api_per_plan = float(required.groupby("test_case").api_cost_repriced.mean().mean())
    variable_costs = (
        required.assign(
            variable_cost=required.debug_cost + required.verification_cost_repriced
        )
        .groupby(["debug_model", "test_case"], sort=True).variable_cost.mean()
        .groupby(level="debug_model").mean()
    )
    rows = []
    for reps in repetitions:
        plan_count = 27 * reps
        attempts = plan_count * len(MATCHED_MODELS)
        api_estimate = plan_count * api_per_plan
        row: dict[str, Any] = {
            "repetitions_per_task": reps,
            "paired_plans": plan_count,
            "debug_attempts_across_candidates": attempts,
            "matched_debug_model_count": len(MATCHED_MODELS),
            "shared_knowledge_api_cost_estimate_repriced": api_estimate,
            "candidate_attempt_cost_estimate_all_models_hybrid": 0.0,
            "campaign_hybrid_estimated_total_cost": 0.0,
            "hardware_rental_included": False,
            "price_rebased": True,
            "candidate_cost_basis": "logged debug stage + repriced verification stage",
        }
        by_model_cost = {}
        for model in MATCHED_MODELS:
            if model not in variable_costs.index:
                continue
            amount = plan_count * float(variable_costs[model])
            by_model_cost[f"variable_cost_{model}"] = amount
            row["candidate_attempt_cost_estimate_all_models_hybrid"] += amount
        row.update(by_model_cost)
        row["campaign_hybrid_estimated_total_cost"] = (
            api_estimate + row["candidate_attempt_cost_estimate_all_models_hybrid"]
        )
        rows.append(row)
    return pd.DataFrame(rows)


def configuration_frontier(
    oof: pd.DataFrame, costs: pd.DataFrame, thresholds: tuple[float, ...]
) -> pd.DataFrame:
    """Build an aggregate reference frontier, not a paired task selector test."""
    task_probability = (
        oof.groupby(["debug_model", GROUP], sort=True).p_adiba_rf_calibrated.mean()
        .groupby(level="debug_model").mean()
    )
    matched = costs[costs.debug_model.isin(MATCHED_MODELS)].dropna(
        subset=["api_cost_repriced", "debug_cost", "verification_cost_repriced"]
    )
    if matched.empty:
        return pd.DataFrame()
    task_cost = (
        matched.assign(
            variable_cost=matched.debug_cost + matched.verification_cost_repriced
        )
        .groupby(["debug_model", "test_case"], sort=True)
        .agg(api_cost=("api_cost_repriced", "mean"), variable_cost=("variable_cost", "mean"))
    )
    shared_api = float(task_cost.groupby(level="test_case").api_cost.mean().mean())
    candidate_cost = task_cost.variable_cost.groupby(level="debug_model").mean()
    candidates = []
    for model in sorted(set(task_probability.index) & set(candidate_cost.index)):
        probability = float(task_probability[model])
        cost = shared_api + float(candidate_cost[model])
        candidates.append(
            {
                "debug_model": model,
                "equal_task_mean_oof_success_probability": probability,
                "shared_api_plan_cost_repriced_mean": shared_api,
                "debug_plus_verifier_cost_hybrid_mean": float(candidate_cost[model]),
                "estimated_selected_attempt_cost_hybrid": cost,
                "estimated_cost_per_success": cost / probability if probability > 0 else math.inf,
                "debug_stage_cost_basis": "logged",
                "api_and_verifier_price_basis": "official standard rates, token counts",
            }
        )
    frontier = pd.DataFrame(candidates)
    efficient = []
    for _, candidate in frontier.iterrows():
        dominated = (
            (frontier.estimated_selected_attempt_cost_hybrid <= candidate.estimated_selected_attempt_cost_hybrid)
            & (frontier.equal_task_mean_oof_success_probability >= candidate.equal_task_mean_oof_success_probability)
            & (
                (frontier.estimated_selected_attempt_cost_hybrid < candidate.estimated_selected_attempt_cost_hybrid)
                | (frontier.equal_task_mean_oof_success_probability > candidate.equal_task_mean_oof_success_probability)
            )
        ).any()
        efficient.append(not bool(dominated))
    frontier["pareto_efficient_reference"] = efficient
    rows = [{"policy": "aggregate_reference_frontier", **r} for r in frontier.to_dict("records")]
    best_value = frontier.sort_values(["estimated_cost_per_success", "debug_model"]).iloc[0]
    rows.append(
        {
            "policy": "minimum_estimated_cost_per_success",
            "target_probability": math.nan,
            "selected_debug_model": best_value.debug_model,
            "equal_task_mean_oof_success_probability": best_value.equal_task_mean_oof_success_probability,
            "estimated_selected_attempt_cost_hybrid": best_value.estimated_selected_attempt_cost_hybrid,
            "estimated_cost_per_success": best_value.estimated_cost_per_success,
            "pareto_efficient_reference": bool(best_value.pareto_efficient_reference),
        }
    )
    for threshold in thresholds:
        eligible = frontier[frontier.equal_task_mean_oof_success_probability >= threshold]
        if eligible.empty:
            best = frontier.sort_values(
                ["equal_task_mean_oof_success_probability", "estimated_selected_attempt_cost_hybrid"],
                ascending=[False, True],
            ).iloc[0]
            rows.append(
                {
                    "policy": "cheapest_at_minimum_probability",
                    "target_probability": threshold,
                    "selected_debug_model": None,
                    "equal_task_mean_oof_success_probability": math.nan,
                    "estimated_selected_attempt_cost_hybrid": math.nan,
                    "estimated_cost_per_success": math.nan,
                    "best_alternative_model": best.debug_model,
                    "best_alternative_probability": best.equal_task_mean_oof_success_probability,
                    "probability_shortfall": threshold - best.equal_task_mean_oof_success_probability,
                    "pareto_efficient_reference": False,
                }
            )
        else:
            selected = eligible.sort_values(
                ["estimated_selected_attempt_cost_hybrid", "equal_task_mean_oof_success_probability", "debug_model"],
                ascending=[True, False, True],
            ).iloc[0]
            rows.append(
                {
                    "policy": "cheapest_at_minimum_probability",
                    "target_probability": threshold,
                    "selected_debug_model": selected.debug_model,
                    "equal_task_mean_oof_success_probability": selected.equal_task_mean_oof_success_probability,
                    "estimated_selected_attempt_cost_hybrid": selected.estimated_selected_attempt_cost_hybrid,
                    "estimated_cost_per_success": selected.estimated_cost_per_success,
                    "best_alternative_model": None,
                    "best_alternative_probability": math.nan,
                    "probability_shortfall": 0.0,
                    "pareto_efficient_reference": bool(selected.pareto_efficient_reference),
                }
            )
    return pd.DataFrame(rows)


def audit_rows(all_rows: pd.DataFrame, labeled: pd.DataFrame, costs: pd.DataFrame) -> dict[str, Any]:
    models = sorted(all_rows.debug_model.astype(str).unique().tolist())
    cost_models = sorted(costs.debug_model.dropna().astype(str).unique().tolist()) if len(costs) else []
    return {
        "handoff_commit": HANDOFF_COMMIT,
        "source_rows": int(len(all_rows)),
        "ground_truth_known_rows": int(len(labeled)),
        "ground_truth_unknown_rows": int(len(all_rows) - len(labeled)),
        "task_scenarios": int(all_rows[GROUP].nunique()),
        "debug_models_in_feature_table": models,
        "debug_models_with_canonical_cost_reference": [model for model in models if model in cost_models],
        "debug_models_without_canonical_cost_reference": [model for model in models if model not in cost_models],
        "numeric_features": NUMERIC_FEATURES,
        "categorical_features": CATEGORICAL_FEATURES,
        "excluded_fields": ["test_name (group only)", "run_status", "verified", "debug_self_report", "duration_s", "debug_input_tokens", "debug_output_tokens", "debug_total_tokens", "label_success (validated only; GT is target)"],
        "canonical_model_identity_mismatch": {
            "feature_table_candidate": "ornith:35b",
            "canonical_cost_candidate": "muse-glimmer:30b",
            "treated_as_same_model": False,
        },
    }


def markdown_table(frame: pd.DataFrame, columns: list[str] | None = None, digits: int = 4) -> str:
    if columns is not None:
        frame = frame[columns]
    if frame.empty:
        return "_No rows available._"
    rendered = frame.copy()
    for col in rendered.columns:
        if pd.api.types.is_float_dtype(rendered[col]):
            rendered[col] = rendered[col].map(lambda value: "—" if pd.isna(value) else f"{value:.{digits}f}")
        else:
            rendered[col] = rendered[col].map(lambda value: "—" if pd.isna(value) else str(value).replace("|", "\\|"))
    headers = list(rendered.columns)
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    lines.extend("| " + " | ".join(map(str, row)) + " |" for row in rendered.itertuples(index=False, name=None))
    return "\n".join(lines)


def make_report(
    output: Path,
    csv_path: Path,
    all_rows: pd.DataFrame,
    labeled: pd.DataFrame,
    workload: pd.DataFrame,
    metrics: pd.DataFrame,
    frontier: pd.DataFrame,
    costs: pd.DataFrame,
    campaign: pd.DataFrame,
    canonical_audit: dict[str, Any],
    logistic_c: float,
    fold_count: int,
) -> None:
    global_metrics = metrics[metrics.scope == "all candidates / pooled attempts"].copy()
    global_metrics = global_metrics.sort_values("brier")
    cost_matched = sorted(set(all_rows.debug_model.astype(str)) & set(costs.debug_model.dropna().astype(str))) if len(costs) else []
    cost_missing = sorted(set(all_rows.debug_model.astype(str)) - set(cost_matched))
    cost_known = costs.dropna(subset=["total_cost"]) if len(costs) else costs
    cost_range = "No usable canonical logged cost records were found."
    if len(cost_known):
        cost_range = f"${cost_known.total_cost.min():.5f}–${cost_known.total_cost.max():.5f} per known canonical attempt (historical logged estimate)."
    hybrid_known = costs.dropna(
        subset=["api_cost_repriced", "debug_cost", "verification_cost_repriced"]
    ) if len(costs) else costs
    hybrid_range = "No complete token-based hybrid cost records were found."
    if len(hybrid_known):
        hybrid_values = (
            hybrid_known.api_cost_repriced
            + hybrid_known.debug_cost
            + hybrid_known.verification_cost_repriced
        )
        hybrid_range = (
            f"${hybrid_values.min():.5f}–${hybrid_values.max():.5f} per known canonical attempt "
            "(API and verifier repriced; debug stage logged)."
        )
    text = f"""# Offline prediction pilot

## Result

This is a development-stage probability-prediction audit, not a deployable selector. Four predictors were evaluated with {fold_count}-fold stratified validation grouped by the full task scenario. All attempts for a held-out scenario stay out of training. The target is `ground_truth_passed`; rows with unknown Ground Truth remain unknown and are excluded from scoring.

The source feature table contains {len(all_rows):,} attempts across {all_rows[GROUP].nunique()} task scenarios and {all_rows.debug_model.nunique()} debug-model identities. {len(labeled):,} attempts have known Ground Truth and {len(all_rows)-len(labeled):,} do not. The source `label_success` column was checked against Ground Truth and was not used as the target.

## Data audit

The pinned input is [Adiba's feature export at commit `{HANDOFF_COMMIT}`]({HANDOFF_CSV_URL}) (`{csv_path.name}`, SHA-256 `{sha256_file(csv_path)}`). It supplies 15 numeric features extracted from the KnowledgeAgent response plus `debug_model`. It does not supply raw plan text, original problem-description text, or a plan hash. Therefore this pilot tests a **numeric-response-feature** predictor, not the agreed full text-plus-plan representation.

The seven handoff candidates are: {', '.join(sorted(all_rows.debug_model.astype(str).unique()))}. The canonical cost exports contain six matching identities: {', '.join(cost_matched) if cost_matched else 'none'}. The handoff uses `ornith:35b`; the canonical exports instead contain `muse-glimmer:30b`. They were not treated as interchangeable. {('No canonical cost reference exists for: ' + ', '.join(cost_missing) + '.') if cost_missing else ''}

The candidate cost reference comes from {canonical_audit.get('parsed_rows', 0):,} canonical rows with {canonical_audit.get('validation_findings', 0):,} integrity findings. The source exports' logged total-cost range is {cost_range} A second, hybrid reference recomputes the `gpt-5-mini` KnowledgeAgent and `gpt-5-nano` verifier stages from recorded input/output token counts using the official standard rates captured on {PRICE_SNAPSHOT_DATE}: $0.25/$2.00 and $0.05/$0.40 per million input/output tokens, respectively. Cache-hit counts are unavailable, so standard input rates are used; both model pages currently mark these models deprecated. The remaining debug-stage cost stays as logged. The hybrid range is {hybrid_range}

For hardware context, [RunPod lists an A40 Secure Cloud reference at $0.59/GPU-hour]({RUNPOD_A40_PRICE_SOURCE}) (price snapshot {PRICE_SNAPSHOT_DATE}). Historical records do not identify the execution host, model-to-device mapping, or billed GPU-occupied seconds. Therefore this rental rate is not added to old run or campaign totals; future paired captures should record those resource facts directly.

The handoff includes {all_rows[GROUP].nunique()} scenario groups. Its workload has repeated attempts, but not a common-KnowledgeAgent-plan key or proof that the same response was replayed across candidate models. The output must not be read as paired counterfactual model-selection evidence.

## Prediction inputs and models

Prediction inputs are exactly `debug_model` and these pre-debug KnowledgeAgent-response features: `{', '.join(NUMERIC_FEATURES)}`. The model excludes scenario name, run status, verification verdict, debug-agent self-report, duration, and debug token counts. Scenario name is used only as the group boundary for validation.

The comparisons are:

1. **Model prior:** each candidate's mean Ground Truth rate over training scenarios, with scenarios weighted equally.
2. **Regularized logistic:** median-imputed and standardized numeric features, one-hot candidate identity, candidate-feature interactions, and L2 logistic regression. The regularization strength is selected using inner grouped cross-validation on Brier score.
3. **Adiba Random Forest:** the handoff's fixed success-classifier structure (500 trees, depth 6, leaf size 5, class-balanced sampling, and an eight-feature selector); preprocessing and selection are fit inside each outer training fold.
4. **Grouped-calibrated Random Forest:** the same forest, with a Platt calibrator trained on inner-fold, task-held-out forest probabilities inside each outer training fold.

Probability quality is assessed primarily with Brier score and log loss; ROC AUC is secondary. The Brier confidence interval resamples whole task scenarios. Calibration bins and per-candidate scores are in the accompanying CSVs. No threshold is tuned on the outer test folds.

## Held-out probability results

{markdown_table(global_metrics, ['predictor', 'n_attempts_gt_known', 'n_attempts_gt_unknown', 'n_task_scenarios', 'brier', 'brier_ci95_low_task_clustered', 'brier_ci95_high_task_clustered', 'log_loss', 'roc_auc_secondary', 'mean_predicted_probability', 'pooled_ground_truth_success_rate', 'equal_task_mean_ground_truth_success_rate'])}

## Aggregate cost/reliability reference

This reference computes an equal-task mean probability from held-out calibrated-RF predictions and combines it with hybrid estimated costs: the common API plan and verifier are repriced from tokens, while debug-stage cost remains logged. It shows the agreed decision rules—cheapest model at a probability threshold, including 100%, and minimum estimated cost per successful completion (`estimated attempt cost / predicted success probability`, assuming independent repeated attempts). It is not a task-conditioned policy evaluation: the input table does not prove a shared plan across candidates, and success and cost come from different export snapshots. Do not interpret a selected row as a validated routing decision.

{markdown_table(frontier[frontier.policy == 'aggregate_reference_frontier'], ['debug_model', 'equal_task_mean_oof_success_probability', 'estimated_selected_attempt_cost_hybrid', 'estimated_cost_per_success', 'pareto_efficient_reference'])}

{markdown_table(frontier[frontier.policy != 'aggregate_reference_frontier'], ['policy', 'target_probability', 'selected_debug_model', 'equal_task_mean_oof_success_probability', 'estimated_selected_attempt_cost_hybrid', 'estimated_cost_per_success', 'best_alternative_model', 'best_alternative_probability', 'probability_shortfall'])}

### Per-candidate workload outcomes

The pooled rate weights each known-GT attempt equally. The equal-task rate first averages attempts within each scenario, then weights scenarios equally. Unknown Ground Truth is shown in the denominator columns, never counted as a failure.

{markdown_table(workload, ['debug_model', 'attempts_total', 'attempts_gt_known', 'attempts_gt_unknown', 'task_scenarios', 'pooled_attempt_success_rate', 'equal_task_mean_success_rate', 'mean_logged_duration_s'])}

## Costed paired-confirmation proposal

The table below estimates a future paired campaign with five, ten, or twenty KnowledgeAgent plans per scenario. Each plan would be generated once and reused across six model identities that match the canonical cost reference; each candidate run would start from a restored fixture. The common API plan and verifier stage use token-based official rates; candidate debug-stage costs use historical logged estimates. Hardware rental is excluded because host occupancy is not known. The seventh handoff candidate is omitted until its identity and cost source are reconciled.

{markdown_table(campaign, ['repetitions_per_task', 'paired_plans', 'debug_attempts_across_candidates', 'shared_knowledge_api_cost_estimate_repriced', 'candidate_attempt_cost_estimate_all_models_hybrid', 'campaign_hybrid_estimated_total_cost'])}

The 5-repetition row means 135 shared plans and 810 candidate debug attempts across the six matched models. Five repeats remain a pilot-sized sample, not a guarantee that an 80% probability estimate is precise. Higher repetitions reduce within-scenario run noise; adding new held-out task scenarios is still required to support claims beyond this fixed suite.

## Readout and next research step

The outer-fold metrics favor the grouped-calibrated Random Forest as the next offline candidate if its Brier score and log loss remain better under confirmation. The saved calibrated-forest and logistic artifacts are research-only. This pilot can test whether response features contain signal on held-out benchmark scenarios and whether probability estimates improve over a per-model workload prior. It cannot validate a selector that sees one exact plan and chooses among candidate models, because the handoff does not prove that candidates share the same KnowledgeAgent response. It also lacks the original user problem text, has one candidate-identity mismatch, and represents only 27 benchmark scenarios.

Next, run an offline paired-data capture experiment: for each scenario and repetition, save the exact KnowledgeAgent response (or a stable hash plus immutable response artifact), replay that response across every candidate debug model, restore the fixture before each attempt, preserve unknown Ground Truth, and retain per-stage cost/resource measures. Keep the KnowledgeAgent and verifier fixed. Hold out entire scenarios for confirmation and report both pooled-attempt and equal-task workload success. Do not integrate live routing until probability calibration, cost coverage, and paired policy performance are confirmed.

## Files

- `oof_predictions.csv`: outer-fold probabilities, including rows whose Ground Truth is unknown.
- `model_metrics.csv`: pooled and per-candidate scores, coverage, and task-clustered Brier intervals.
- `calibration_bins.csv`: observed Ground Truth by predicted-probability bin.
- `workload_by_model.csv`: pooled and equal-task success summaries.
- `configuration_frontier.csv`: aggregate reference frontier and threshold decisions, explicitly unpaired.
- `paired_campaign_estimates.csv`: hybrid API/verifier repricing and logged debug-cost campaign scenarios.
- `canonical_cost_reference_rows.csv`: canonical per-attempt cost and token records, with original logged costs and API/verifier repricing columns.
- `research_predictor.joblib`: full-data forest plus grouped out-of-fold Platt calibrator; offline research only.
- `research_predictor_logistic.joblib`: full-data regularized logistic candidate pipeline.
- `training_manifest.json`: hashes, features, splits, and provenance.
"""
    output.write_text(text, encoding="utf-8")


def run(args: argparse.Namespace) -> int:
    feature_path = args.feature_csv.resolve()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    all_rows, labeled, all_features = load_feature_data(feature_path)
    x_labeled = all_features.loc[labeled.index].reset_index(drop=True)
    y_labeled = labeled[TARGET].astype(int).reset_index(drop=True)
    groups = labeled[GROUP].astype(str).reset_index(drop=True)
    folds = grouped_splits(y_labeled, groups, args.folds, args.seed)
    fold_count = len(folds)

    oof_records: list[pd.DataFrame] = []
    tuning_rows: list[dict[str, Any]] = []
    for fold, (train_idx, valid_idx) in enumerate(folds, start=1):
        train_labeled = labeled.iloc[train_idx].copy()
        train_groups = set(train_labeled[GROUP].astype(str))
        valid_groups = set(labeled.iloc[valid_idx][GROUP].astype(str))
        train_x = x_labeled.iloc[train_idx]
        train_y = y_labeled.iloc[train_idx]
        # Keep all held-out rows (including those with unknown Ground Truth)
        # so they receive a prediction without acquiring an imputed label.
        valid_indices = all_rows.index[all_rows[GROUP].astype(str).isin(valid_groups)]
        valid_all = all_rows.loc[valid_indices].copy().reset_index(drop=True)
        valid_x = all_features.loc[valid_indices].reset_index(drop=True)

        c_value, c_scores = choose_logistic_c(
            train_x, train_y, train_labeled[GROUP].astype(str).reset_index(drop=True), args.seed + fold, args.folds
        )
        tuning_rows.extend([{"outer_fold": fold, "selected_C": c_value, **score} for score in c_scores])

        model_prior = model_prior_predictions(train_labeled, valid_all)
        logistic = logistic_pipeline(c_value)
        logistic.fit(train_x, train_y)
        p_logistic = logistic.predict_proba(valid_x)[:, 1]

        calibrator = fit_grouped_rf_calibrator(
            train_x.reset_index(drop=True),
            train_y.reset_index(drop=True),
            train_labeled[GROUP].astype(str).reset_index(drop=True),
            args.seed + fold * 100,
            args.folds,
        )
        forest = adiba_random_forest_pipeline(args.seed + fold)
        forest.fit(train_x, train_y)
        p_forest = forest.predict_proba(valid_x)[:, 1]
        p_forest_calibrated = apply_rf_calibrator(calibrator, p_forest)

        result = valid_all[[GROUP, "debug_model", TARGET]].copy()
        result.insert(0, "outer_fold", fold)
        result["p_model_prior"] = model_prior
        result["p_logistic"] = p_logistic
        result["p_adiba_rf"] = p_forest
        result["p_adiba_rf_calibrated"] = p_forest_calibrated
        oof_records.append(result)

    oof = pd.concat(oof_records, ignore_index=True).sort_values([GROUP, "debug_model", "outer_fold"]).reset_index(drop=True)
    metrics = build_metrics(oof, args.seed, args.bootstrap_reps)
    calibration = calibration_table(oof)
    workload = workload_table(all_rows)
    tuning = pd.DataFrame(tuning_rows)

    costs, cost_audit = canonical_cost_reference(args.canonical_data)
    frontier = configuration_frontier(oof, costs, tuple(args.thresholds))
    campaign = paired_campaign_estimates(costs, tuple(args.campaign_repetitions))
    audit = audit_rows(all_rows, labeled, costs)
    audit.update(
        {
            "feature_csv_sha256": sha256_file(feature_path),
            "feature_csv_path": str(feature_path),
            "canonical_data_path": str(args.canonical_data.resolve()),
            "canonical_data_audit": cost_audit,
            "outer_grouped_folds": fold_count,
            "random_seed": args.seed,
            "sklearn_version": sklearn.__version__,
            "exact_plan_replay_key_present": False,
            "original_problem_description_in_feature_csv": False,
        }
    )

    # Fit a reusable development artifact using grouped CV on all labeled rows
    # to select regularization, then fit once on all known-GT observations.
    full_c, full_scores = choose_logistic_c(x_labeled, y_labeled, groups, args.seed + 10_000, args.folds)
    final_model = logistic_pipeline(full_c)
    final_model.fit(x_labeled, y_labeled)
    joblib.dump(final_model, output / "research_predictor_logistic.joblib")
    rf_calibrator = fit_grouped_rf_calibrator(
        x_labeled, y_labeled, groups, args.seed + 20_000, args.folds
    )
    final_forest = adiba_random_forest_pipeline(args.seed + 30_000)
    final_forest.fit(x_labeled, y_labeled)
    joblib.dump(
        {
            "base_model": final_forest,
            "calibrator": rf_calibrator,
            "features": NUMERIC_FEATURES + CATEGORICAL_FEATURES,
            "target": TARGET,
            "calibration": "Platt scaling trained from grouped out-of-fold forest probabilities",
            "scope": "offline research only; not approved for live routing",
        },
        output / "research_predictor.joblib",
    )
    audit["full_data_logistic_C"] = full_c
    audit["full_data_inner_grouped_brier_by_C"] = full_scores
    audit["artifact_scope"] = "offline research; calibrated in grouped folds but not cleared for live routing"

    oof.to_csv(output / "oof_predictions.csv", index=False)
    metrics.to_csv(output / "model_metrics.csv", index=False)
    calibration.to_csv(output / "calibration_bins.csv", index=False)
    workload.to_csv(output / "workload_by_model.csv", index=False)
    frontier.to_csv(output / "configuration_frontier.csv", index=False)
    tuning.to_csv(output / "logistic_inner_selection.csv", index=False)
    campaign.to_csv(output / "paired_campaign_estimates.csv", index=False)
    costs.to_csv(output / "canonical_cost_reference_rows.csv", index=False)
    (output / "training_manifest.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    make_report(
        output / "prediction_pilot_report.md",
        feature_path,
        all_rows,
        labeled,
        workload,
        metrics,
        frontier,
        costs,
        campaign,
        cost_audit,
        full_c,
        fold_count,
    )
    print(f"Wrote grouped prediction pilot to {output}")
    print(metrics[metrics.scope == "all candidates / pooled attempts"][["predictor", "brier", "log_loss", "roc_auc_secondary"]].to_string(index=False))
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature-csv", type=Path, required=True, help="Pinned Adiba handoff feature CSV")
    parser.add_argument("--canonical-data", type=Path, default=Path("data"), help="Canonical KubeLLM exports used only for cost context")
    parser.add_argument("--output-dir", type=Path, default=Path(".local/prediction_pilot/report"))
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--bootstrap-reps", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=20261017)
    parser.add_argument("--campaign-repetitions", type=int, nargs="+", default=[5, 10, 20])
    parser.add_argument("--thresholds", type=float, nargs="+", default=[0.8, 0.9, 0.95, 0.99, 1.0])
    args = parser.parse_args()
    if args.folds < 2 or args.bootstrap_reps < 1:
        parser.error("--folds must be at least 2 and --bootstrap-reps must be positive")
    if not args.canonical_data.is_dir():
        parser.error(f"Canonical data directory not found: {args.canonical_data}")
    if any(value < 1 for value in args.campaign_repetitions):
        parser.error("campaign repetition counts must be positive")
    if any(value < 0 or value > 1 for value in args.thresholds):
        parser.error("probability thresholds must be between 0 and 1")
    return args


if __name__ == "__main__":
    raise SystemExit(run(parse_args()))
