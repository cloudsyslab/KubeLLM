"""Compare a median baseline and eight RF runtime ablations per debug model.

All selection, imputation, and outlier fences are fit inside training folds.
Held-out metrics are diagnostic only; the winner is chosen by training CV.
"""

import argparse
import itertools
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import TransformedTargetRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.feature_selection import SelectFromModel
from sklearn.impute import SimpleImputer
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from case_majority_metrics import case_runtime_metrics
from train_random_forest import NUMERIC_FEATURES
from train_runtime_predictor import load_selected_model, remove_training_outliers, split_case_groups
from train_test_cases import safe_slug


def configurations():
    return [dict(name='median_baseline', features='none', target='raw', outliers=False)] + [
        dict(name=f'rf_{features}_{target}_outliers_{"on" if outliers else "off"}',
             features=features, target=target, outliers=outliers)
        for features, target, outliers in itertools.product(
            ['all', 'selected'], ['raw', 'log'], [False, True])]


def make_rf(config, args):
    settings = dict(n_estimators=args.trees, max_depth=args.max_depth,
                    min_samples_leaf=args.min_samples_leaf, max_features='sqrt',
                    random_state=args.seed, n_jobs=args.jobs)
    steps = [('imputer', SimpleImputer(strategy='median', keep_empty_features=True)),
             ('normalizer', StandardScaler())]
    if config['features'] == 'selected':
        steps.append(('selector', SelectFromModel(RandomForestRegressor(**settings),
                      threshold=-np.inf, max_features=args.selected_features)))
    steps.append(('regressor', RandomForestRegressor(**settings)))
    pipeline = Pipeline(steps)
    if config['target'] == 'log':
        return TransformedTargetRegressor(regressor=pipeline, func=np.log1p,
                                          inverse_func=np.expm1)
    return pipeline


def fit_candidate(frame, config, args):
    fitting, removed, info = remove_training_outliers(
        frame, args.outlier_iqr_multiplier if config['outliers'] else 0)
    median = float(fitting.duration_s.median())
    if config['name'] == 'median_baseline':
        return None, median, [], removed, info
    estimator = make_rf(config, args)
    estimator.fit(fitting[NUMERIC_FEATURES], fitting.duration_s)
    pipeline = estimator.regressor_ if config['target'] == 'log' else estimator
    selector = pipeline.named_steps.get('selector')
    features = (list(NUMERIC_FEATURES) if selector is None else
                np.asarray(NUMERIC_FEATURES)[selector.get_support()].tolist())
    return estimator, median, features, removed, info


def predict(estimator, median, frame):
    values = (np.full(len(frame), median) if estimator is None else
              np.maximum(estimator.predict(frame[NUMERIC_FEATURES]), 0))
    if not np.isfinite(values).all():
        raise ValueError('Non-finite runtime predictions')
    return values


def run_model(name, args):
    data = load_selected_model(args.input, name)
    train, test, train_cases, test_cases, split = split_case_groups(
        data, args.test_cases, args.train_fraction, args.seed)
    train = train.loc[train.duration_available].copy()
    test = test.loc[test.duration_available].copy()
    folds = min(args.cv_folds, train.test_name.nunique())
    if folds < 2 or test.empty:
        raise ValueError('Need at least two valid training cases and one valid test case')
    splits = list(GroupKFold(folds).split(train, groups=train.test_name))
    destination = args.output_dir / safe_slug(name)
    destination.mkdir(parents=True, exist_ok=True)
    trials, fold_tables = [], []
    for config in configurations():
        print(f'  {config["name"]}', flush=True)
        oof = np.full(len(train), np.nan)
        fold_scores = []
        for fold, (fitting_index, validation_index) in enumerate(splits, 1):
            fitting, validation = train.iloc[fitting_index], train.iloc[validation_index]
            estimator, median, features, _, info = fit_candidate(fitting, config, args)
            values = predict(estimator, median, validation)
            oof[validation_index] = values
            metrics, _ = case_runtime_metrics(validation, values, median, args.tolerance_percent)
            fold_scores.append(metrics['mae_seconds' if args.select_by == 'mae' else 'mape_percent'])
            fold_tables.append(dict(candidate=config['name'], fold=fold,
                fitting_cases=json.dumps(sorted(fitting.test_name.unique())),
                validation_cases=json.dumps(sorted(validation.test_name.unique())),
                selected_features=json.dumps(features), outliers_removed=len(fitting)-info['training_rows_after'],
                mae_seconds=metrics['mae_seconds'], mape_percent=metrics['mape_percent']))
        # Pool case-level OOF predictions: every training case gets equal weight.
        metrics, cases = case_runtime_metrics(train, oof, float(train.duration_s.median()), args.tolerance_percent)
        cases.to_csv(destination / f'{config["name"]}_cv_cases.csv', index=False)
        trials.append({**config, 'cv_mae_seconds': metrics['mae_seconds'],
                       'cv_mape_percent': metrics['mape_percent'],
                       'cv_fold_score_std': float(np.std(fold_scores))})
    metric = 'cv_mae_seconds' if args.select_by == 'mae' else 'cv_mape_percent'
    winner = min(trials, key=lambda row: row[metric])['name']
    pd.DataFrame(trials).to_csv(destination / 'cv_comparison.csv', index=False)
    pd.DataFrame(fold_tables).to_csv(destination / 'cv_folds.csv', index=False)
    reports, all_cases, all_runs = [], [], []
    winner_details = None
    for config, cv in zip(configurations(), trials):
        estimator, median, features, removed, info = fit_candidate(train, config, args)
        values = predict(estimator, median, test)
        metrics, cases = case_runtime_metrics(test, values, median, args.tolerance_percent)
        cases.insert(0, 'candidate', config['name'])
        all_cases.append(cases)
        runs = test[['debug_model', 'test_name', 'duration_s']].copy()
        runs.insert(0, 'candidate', config['name'])
        runs['predicted_duration_s'] = values
        all_runs.append(runs)
        reports.append(dict(debug_model=name, **cv, selected_by_cv=config['name'] == winner,
            test_mae_seconds=metrics['mae_seconds'], test_mape_percent=metrics['mape_percent'],
            test_rmse_seconds=metrics['rmse_seconds'], test_r2=metrics['r2'],
            test_within_tolerance_percent=metrics['within_tolerance_accuracy_percent'],
            actual_total_minutes=metrics['total_actual_repeated_runs_minutes'],
            predicted_total_minutes=metrics['total_predicted_repeated_runs_minutes'],
            selected_features=json.dumps(features), training_outliers_removed=len(removed)))
        if config['name'] == winner:
            joblib.dump(dict(estimator=estimator, median_seconds=median,
                numeric_features=list(NUMERIC_FEATURES), configuration=config), destination / 'winner.joblib')
            removed.to_csv(destination / 'winner_removed_training_outliers.csv', index=False)
            winner_details = dict(configuration=config, selected_features=features,
                                  outlier_removal=info, test_runtime_metrics=metrics)
    baseline = reports[0]
    for report in reports:
        report['test_mae_improvement_vs_baseline_seconds'] = baseline['test_mae_seconds']-report['test_mae_seconds']
        report['test_mape_improvement_vs_baseline_percentage_points'] = baseline['test_mape_percent']-report['test_mape_percent']
    pd.DataFrame(reports).to_csv(destination / 'comparison.csv', index=False)
    pd.concat(all_cases).to_csv(destination / 'case_predictions.csv', index=False)
    pd.concat(all_runs).to_csv(destination / 'run_predictions.csv', index=False)
    details = dict(debug_model=name, input=str(args.input), seed=args.seed,
        train_cases=train_cases, test_cases=test_cases, split_method=split,
        cv_folds=folds, selection_metric=args.select_by, winner=winner_details,
        note='Winner chosen by pooled training-case OOF errors only. Held-out candidate comparisons are diagnostic, not tuning evidence.')
    (destination / 'metrics.json').write_text(json.dumps(details, indent=2, allow_nan=False)+'\n')
    print(f'  CV winner ({args.select_by}): {winner}', flush=True)
    return reports


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=Path('data/all_7_models_features.csv'))
    parser.add_argument('--output-dir', type=Path, default=Path('data/runtime_comparison_25_2'))
    parser.add_argument('--debug-model', help='Omit to compare all debug models separately')
    split = parser.add_mutually_exclusive_group()
    split.add_argument('--test-cases', nargs='+')
    split.add_argument('--train-fraction', type=float)
    parser.add_argument('--select-by', choices=['mae', 'mape'], default='mae')
    parser.add_argument('--selected-features', type=int, default=8)
    parser.add_argument('--cv-folds', type=int, default=5)
    parser.add_argument('--trees', type=int, default=200)
    parser.add_argument('--max-depth', type=int, default=8)
    parser.add_argument('--min-samples-leaf', type=int, default=2)
    parser.add_argument('--jobs', type=int, default=-1)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--outlier-iqr-multiplier', type=float, default=1.5)
    parser.add_argument('--tolerance-percent', type=float, default=20)
    args = parser.parse_args()
    if args.test_cases is None and args.train_fraction is None:
        args.test_cases = ['missing_dependency', 'port_mismatch_wrong_interface']
    if args.test_cases and len(set(args.test_cases)) != len(args.test_cases):
        parser.error('Test case names must be unique')
    if args.train_fraction is not None and not 0 < args.train_fraction < 1:
        parser.error('Train fraction must be between 0 and 1')
    if not 1 <= args.selected_features <= len(NUMERIC_FEATURES):
        parser.error('Invalid selected-feature count')
    if args.cv_folds < 2 or min(args.trees, args.max_depth, args.min_samples_leaf) < 1 or args.jobs == 0:
        parser.error('Invalid RF or CV settings')
    if not np.isfinite(args.outlier_iqr_multiplier) or args.outlier_iqr_multiplier <= 0:
        parser.error('Outlier multiplier must be positive and finite for the on/off comparison')
    if not np.isfinite(args.tolerance_percent) or args.tolerance_percent < 0:
        parser.error('Tolerance must be non-negative and finite')
    frame = pd.read_csv(args.input)
    names = [args.debug_model] if args.debug_model else sorted(frame.debug_model.dropna().astype(str).unique())
    args.output_dir.mkdir(parents=True, exist_ok=True)
    reports = []
    for name in names:
        print(f'\n=== {name} ===', flush=True)
        reports.extend(run_model(name, args))
    table = pd.DataFrame(reports)
    table.to_csv(args.output_dir / 'all_comparisons.csv', index=False)
    winners = table.loc[table.selected_by_cv]
    winners.to_csv(args.output_dir / 'summary.csv', index=False)
    print(winners[['debug_model', 'name', 'test_mae_seconds', 'test_mape_percent']].to_string(index=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
