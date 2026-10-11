"""Select features by training-only grouped CV, separately for each debug model.

The final test cases are never used to choose a feature selector or RF settings.
Success and duration use separate selectors because they have different targets.
"""

import argparse
import json
from functools import partial
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import TransformedTargetRegressor
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.feature_selection import RFE, SelectFromModel, SelectKBest
from sklearn.feature_selection import mutual_info_classif, mutual_info_regression
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, balanced_accuracy_score, mean_absolute_error
from sklearn.model_selection import GroupKFold, StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler

from train_random_forest import NUMERIC_FEATURES
from train_test_cases import evaluate_predictions, safe_slug
from case_majority_metrics import majority_case_metrics, case_runtime_metrics
from train_runtime_predictor import (
    evaluate_runtime_predictions, load_selected_model, remove_training_outliers,
    split_case_groups,
)


def make_model(task, config, trees, seed):
    regression = task == 'runtime'
    estimator_type = RandomForestRegressor if regression else RandomForestClassifier
    settings = dict(n_estimators=trees, max_depth=config['max_depth'],
                    min_samples_leaf=config['min_samples_leaf'], max_features='sqrt',
                    random_state=seed, n_jobs=-1)
    if not regression:
        settings['class_weight'] = 'balanced_subsample'
    steps = [('imputer', SimpleImputer(strategy='median', keep_empty_features=True)),
             ('log1p', FunctionTransformer(np.log1p, feature_names_out='one-to-one')),
             ('normalizer', StandardScaler())]
    method, k = config['method'], config['k']
    if method == 'rf_importance':
        selector = SelectFromModel(estimator_type(**settings), threshold=-np.inf,
                                   max_features=k)
    elif method == 'mutual_info':
        score = mutual_info_regression if regression else mutual_info_classif
        selector = SelectKBest(partial(score, random_state=seed), k=k)
    elif method == 'rfe':
        selector = RFE(estimator_type(**settings), n_features_to_select=k, step=3)
    else:
        selector = None
    if selector is not None:
        steps.append(('selector', selector))
    steps.append(('regressor' if regression else 'classifier', estimator_type(**settings)))
    pipeline = Pipeline(steps)
    if regression:
        return TransformedTargetRegressor(regressor=pipeline, func=np.log1p,
                                          inverse_func=np.expm1)
    return pipeline


def configurations(args):
    # The previous per-model RF settings are included as an all-feature baseline.
    configs = [{'method': 'none', 'k': len(NUMERIC_FEATURES),
                'max_depth': 6, 'min_samples_leaf': 5}]
    for depth, leaf in [(6, 5), (8, 2), (None, 1)]:
        for method in args.methods:
            sizes = [len(NUMERIC_FEATURES)] if method == 'none' else args.feature_counts
            for k in sizes:
                config = dict(method=method, k=k, max_depth=depth, min_samples_leaf=leaf)
                if config not in configs:
                    configs.append(config)
    return configs


def tune(train, task, args, destination):
    target = 'duration_s' if task == 'runtime' else 'label_success'
    valid = train['duration_available'] if task == 'runtime' else train[target].notna()
    usable = train.loc[valid].copy()
    if task == 'success' and usable[target].nunique() != 2:
        raise ValueError('Success training requires both PASS and FAIL labels')
    folds = min(args.cv_folds, usable['test_name'].nunique())
    if folds < 2:
        raise ValueError('At least two training test cases are required for feature selection')
    splitter = (GroupKFold(folds) if task == 'runtime' else
                StratifiedGroupKFold(folds, shuffle=True, random_state=args.seed))
    splits = list(splitter.split(usable[NUMERIC_FEATURES], usable[target], usable['test_name']))
    trials = []
    for config in configurations(args):
        scores = []
        failure = None
        try:
            for train_index, validation_index in splits:
                fitting = usable.iloc[train_index]
                validation = usable.iloc[validation_index]
                if set(fitting.test_name) & set(validation.test_name):
                    raise RuntimeError('Group leakage in cross-validation')
                if task == 'runtime':
                    fitting, _, _ = remove_training_outliers(fitting, args.outlier_iqr_multiplier)
                elif fitting[target].nunique() != 2:
                    raise ValueError('A CV training fold contains only one success class')
                model = make_model(task, config, args.trees, args.seed)
                model.fit(fitting[NUMERIC_FEATURES], fitting[target])
                predicted = model.predict(validation[NUMERIC_FEATURES])
                if task == 'runtime':
                    if getattr(args, 'runtime_metric_unit', 'case') == 'case':
                        case_time, _ = case_runtime_metrics(validation, predicted,
                            float(fitting.duration_s.median()), args.accuracy_tolerance_percent)
                        score = -case_time['mae_seconds']
                    else:
                        score = -mean_absolute_error(validation[target], predicted)
                else:
                    if getattr(args, 'accuracy_unit', 'case') == 'case':
                        case_metrics, _ = majority_case_metrics(validation, predicted)
                        score = case_metrics[args.scoring]
                        if args.scoring == 'balanced_accuracy' and score is None:
                            score = case_metrics['accuracy']
                        if score is None:
                            raise ValueError('No unambiguous actual majority in a validation fold')
                    else:
                        metric = accuracy_score if args.scoring == 'accuracy' else balanced_accuracy_score
                        score = metric(validation[target], predicted)
                scores.append(float(score))
        except ValueError as exc:
            failure = str(exc)
        trials.append({**config, 'cv_score': float(np.mean(scores)) if failure is None else None,
                       'cv_std': float(np.std(scores)) if failure is None else None,
                       'fold_scores': json.dumps(scores), 'error': failure})
    table = pd.DataFrame(trials).sort_values('cv_score', ascending=False, na_position='last', kind='stable')
    table.to_csv(destination / f'{task}_cv_comparison.csv', index=False)
    valid_trials = [trial for trial in trials if trial['cv_score'] is not None]
    if not valid_trials:
        raise ValueError(f'All {task} candidates failed; inspect the CV comparison CSV')
    winner = max(valid_trials, key=lambda trial: trial['cv_score'])
    config = {key: winner[key] for key in ['method', 'k', 'max_depth', 'min_samples_leaf']}
    fit_rows = usable
    outliers = None
    if task == 'runtime':
        fit_rows, removed, outliers = remove_training_outliers(usable, args.outlier_iqr_multiplier)
        removed.to_csv(destination / 'removed_training_outliers.csv', index=False)
    model = make_model(task, config, args.trees, args.seed)
    model.fit(fit_rows[NUMERIC_FEATURES], fit_rows[target])
    pipeline = model.regressor_ if task == 'runtime' else model
    selector = pipeline.named_steps.get('selector')
    selected = list(NUMERIC_FEATURES) if selector is None else np.asarray(NUMERIC_FEATURES)[selector.get_support()].tolist()
    print(f'  {task}: {config}; training CV score={winner["cv_score"]:.4f}', flush=True)
    return model, dict(configuration=config, selected_features=selected,
                       cv_score=winner['cv_score'], cv_std=winner['cv_std'], cv_folds=folds,
                       scoring='negative_mae_seconds' if task == 'runtime' else args.scoring,
                       accuracy_unit='run' if task == 'runtime' else getattr(args, 'accuracy_unit', 'case'),
                       metric_unit=(getattr(args, 'runtime_metric_unit', 'case') if task == 'runtime'
                                    else getattr(args, 'accuracy_unit', 'case')),
                       training_rows=len(fit_rows), outlier_removal=outliers), fit_rows


def run_model(model_name, args):
    selected = load_selected_model(args.input, model_name)
    if 'label_success' not in selected:
        raise ValueError('Input must include label_success')
    labels = pd.to_numeric(selected.label_success, errors='raise')
    if not labels.dropna().isin([0, 1]).all():
        raise ValueError('label_success must contain 0, 1, or missing values')
    selected['label_success'] = labels
    train, test, train_names, test_names, split_method = split_case_groups(
        selected, args.test_cases, args.train_fraction, args.seed)
    destination = args.output_dir / safe_slug(model_name)
    destination.mkdir(parents=True, exist_ok=True)
    success_model, success_selection, success_train = tune(train, 'success', args, destination)
    runtime_model, runtime_selection, runtime_train = tune(train, 'runtime', args, destination)
    predictions = success_model.predict(test[NUMERIC_FEATURES])
    scores = success_model.predict_proba(test[NUMERIC_FEATURES])[:, list(success_model.classes_).index(1)]
    duration = np.maximum(runtime_model.predict(test[NUMERIC_FEATURES]), 0.0)
    if not np.isfinite(duration).all():
        raise ValueError('Non-finite runtime prediction')
    success_mask = test.label_success.notna().to_numpy()
    if not success_mask.any():
        raise ValueError('Held-out cases contain no success labels')
    evaluation = evaluate_predictions(test.loc[success_mask, 'label_success'],
        predictions[success_mask], scores[success_mask],
        int(success_train.label_success.mean() >= 0.5))
    # Classification reports contain classification metrics only. Duration
    # errors are reported separately against actual runtimes in seconds.
    for key in ('mae_on_probabilities', 'mape_on_probabilities',
                'r2_on_probabilities', 'regression_metric_basis', 'mape_note'):
        evaluation.pop(key, None)
    if 'metric_note' in evaluation:
        evaluation['metric_note'] = (
            'Balanced accuracy, ROC-AUC, and average precision are null because '
            'the labeled held-out rows contain only one class.'
        )
    case_evaluation, case_votes = majority_case_metrics(test, predictions)
    case_baseline, _ = majority_case_metrics(test, np.full(len(test),
        int(success_train.label_success.mean() >= 0.5)))
    case_evaluation['majority_baseline_accuracy'] = case_baseline['accuracy']
    case_votes.to_csv(destination / 'case_majority_predictions.csv', index=False)
    accuracy_unit = getattr(args, 'accuracy_unit', 'case')
    primary_evaluation = case_evaluation if accuracy_unit == 'case' else evaluation
    if primary_evaluation['accuracy'] is None:
        raise ValueError('Held-out cases have no unambiguous actual majority')
    time_mask = test.duration_available.to_numpy()
    runtime_evaluation = evaluate_runtime_predictions(test.loc[time_mask, 'duration_s'].to_numpy(),
        duration[time_mask], float(runtime_train.duration_s.median()), args.accuracy_tolerance_percent)
    case_time_evaluation, case_times = case_runtime_metrics(test, duration,
        float(runtime_train.duration_s.median()), args.accuracy_tolerance_percent)
    keys = [c for c in ['debug_model', 'test_name'] if c in case_votes]
    case_votes.merge(case_times, on=keys, validate='one_to_one').to_csv(
        destination / 'case_summary.csv', index=False)
    runtime_metric_unit = getattr(args, 'runtime_metric_unit', 'case')
    primary_time = case_time_evaluation if runtime_metric_unit == 'case' else runtime_evaluation
    metadata = [c for c in ['dataset', 'iteration', 'debug_model', 'test_name', 'run_status', 'label_success'] if c in test]
    output = test[metadata].copy()
    output['predicted_success'] = predictions
    output['success_score'] = scores
    output['success_scored'] = success_mask
    output['actual_total_duration_s'] = test.duration_s
    output['predicted_total_duration_s'] = duration
    output['predicted_total_duration_minutes'] = duration / 60
    output.to_csv(destination / 'predictions_with_time.csv', index=False)
    for task, model, selection in [('success', success_model, success_selection), ('runtime', runtime_model, runtime_selection)]:
        artifact = dict(task=task, feature_columns=list(NUMERIC_FEATURES),
                        numeric_features=list(NUMERIC_FEATURES), debug_model=model_name,
                        train_cases=train_names, test_cases=test_names, selection=selection,
                        accuracy_unit=accuracy_unit if task == 'success' else 'run',
                        target='label_success' if task == 'success' else 'duration_s')
        artifact['pipeline' if task == 'success' else 'model'] = model
        joblib.dump(artifact, destination / f'{task}_model.joblib')
    payload = dict(debug_model=model_name, input=str(args.input), seed=args.seed,
                   train_cases=train_names, test_cases=test_names, split_method=split_method,
                   success_selection=success_selection, runtime_selection=runtime_selection,
                   accuracy_unit=accuracy_unit, success_metrics=evaluation,
                   case_success_metrics=case_evaluation, runtime_metrics=runtime_evaluation,
                   runtime_metric_unit=runtime_metric_unit, case_runtime_metrics=case_time_evaluation,
                   selection_note='All candidates selected using training-case CV only; test cases used once.')
    (destination / 'metrics.json').write_text(json.dumps(payload, indent=2, allow_nan=False) + '\n')
    return dict(debug_model=model_name, status='OK', accuracy=primary_evaluation['accuracy'],
                accuracy_unit=accuracy_unit, run_accuracy=evaluation['accuracy'],
                case_accuracy=case_evaluation['accuracy'], scored_cases=case_evaluation['scored_cases'],
                f1=primary_evaluation['f1'], success_selector=success_selection['configuration']['method'],
                success_feature_count=len(success_selection['selected_features']),
                runtime_metric_unit=runtime_metric_unit,
                runtime_mae_seconds=primary_time['mae_seconds'],
                runtime_mape_percent=primary_time['mape_percent'], runtime_r2=primary_time['r2'],
                runtime_accuracy_percent=primary_time['within_tolerance_accuracy_percent'],
                case_runtime_mae_seconds=case_time_evaluation['mae_seconds'],
                case_runtime_mape_percent=case_time_evaluation['mape_percent'],
                run_runtime_mae_seconds=runtime_evaluation['mae_seconds'],
                run_runtime_mape_percent=runtime_evaluation['mape_percent'],
                predicted_heldout_total_minutes=float(duration.sum()/60))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=Path('data/all_7_models_features.csv'))
    parser.add_argument('--output-dir', type=Path, default=Path('data/feature_selection_with_time'))
    parser.add_argument('--debug-model', help='Omit to train all models separately')
    split = parser.add_mutually_exclusive_group()
    split.add_argument('--test-cases', nargs='+')
    split.add_argument('--train-fraction', type=float)
    parser.add_argument('--methods', nargs='+', choices=['none', 'rf_importance', 'mutual_info', 'rfe'],
                        default=['none', 'rf_importance', 'mutual_info', 'rfe'])
    parser.add_argument('--feature-counts', nargs='+', type=int, default=[5, 8, 12])
    parser.add_argument('--cv-folds', type=int, default=3)
    parser.add_argument('--scoring', choices=['accuracy', 'balanced_accuracy'], default='accuracy')
    parser.add_argument('--accuracy-unit', choices=['case', 'run'], default='case',
                        help='Case: majority-vote repeated labeled runs for CV and final accuracy (default)')
    parser.add_argument('--runtime-metric-unit', choices=['case', 'run'], default='case',
                        help='Case: compare mean actual/predicted time per case for CV and final timing metrics')
    parser.add_argument('--trees', type=int, default=100)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--outlier-iqr-multiplier', type=float, default=1.5)
    parser.add_argument('--accuracy-tolerance-percent', type=float, default=20)
    args = parser.parse_args()
    if args.cv_folds < 2 or args.trees < 1:
        parser.error('--cv-folds must be >=2 and --trees >=1')
    if any(k < 1 or k > len(NUMERIC_FEATURES) for k in args.feature_counts):
        parser.error(f'--feature-counts must be between 1 and {len(NUMERIC_FEATURES)}')
    if args.test_cases and len(args.test_cases) != len(set(args.test_cases)):
        parser.error('--test-cases must be unique')
    if not args.test_cases and args.train_fraction is None:
        args.train_fraction = 0.9
    if args.train_fraction is not None and not 0 < args.train_fraction < 1:
        parser.error('--train-fraction must be between 0 and 1')
    if any(not np.isfinite(v) or v < 0 for v in [args.outlier_iqr_multiplier, args.accuracy_tolerance_percent]):
        parser.error('Outlier multiplier and accuracy tolerance must be finite and non-negative')
    data = pd.read_csv(args.input)
    models = [args.debug_model] if args.debug_model else sorted(data.debug_model.dropna().astype(str).unique())
    args.output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for model in models:
        print(f'\n=== {model} ===', flush=True)
        try:
            results.append(run_model(model, args))
        except ValueError as exc:
            print(f'  ERROR: {exc}', flush=True)
            results.append(dict(debug_model=model, status='ERROR', error=str(exc)))
    summary = pd.DataFrame(results)
    summary.to_csv(args.output_dir / 'summary.csv', index=False)
    print('\n' + summary.to_string(index=False))
    print(f'Outputs: {args.output_dir}; totals cover sequential held-out runs.')
    return int(any(row['status'] == 'ERROR' for row in results))


if __name__ == '__main__':
    raise SystemExit(main())
