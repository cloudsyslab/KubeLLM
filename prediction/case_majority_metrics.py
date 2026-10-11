"""Score each test case once by majority voting its repeated labeled runs."""

import numpy as np
import pandas as pd


def majority_case_metrics(frame, predictions):
    """Ignore unknown actual labels; actual ties are unscored, prediction ties wrong.

    Actual and predicted votes use the same labeled runs. No minimum run count
    is imposed: the exported counts expose missing labels or shorter experiments.
    """
    predictions = np.asarray(predictions)
    if predictions.shape != (len(frame),) or not np.isin(predictions, [0, 1]).all():
        raise ValueError('Expected one binary prediction per input run')
    labels = pd.to_numeric(frame['label_success'], errors='raise')
    if not labels.dropna().isin([0, 1]).all():
        raise ValueError('Actual labels must be 0, 1, or missing')
    votes = frame[['test_name']].copy()
    votes['label_success'] = labels
    votes['predicted_success'] = predictions
    keys = ['debug_model', 'test_name'] if 'debug_model' in frame else ['test_name']
    if 'debug_model' in keys:
        votes['debug_model'] = frame['debug_model']
    if votes[keys].isna().any(axis=None):
        raise ValueError('Majority voting requires non-missing model/case identifiers')
    rows = []
    for key, group in votes.groupby(keys, sort=True):
        key = key if isinstance(key, tuple) else (key,)
        known = group.loc[group.label_success.notna()]
        actual_pass = int(known.label_success.eq(1).sum())
        actual_fail = int(known.label_success.eq(0).sum())
        predicted_pass = int(known.predicted_success.eq(1).sum())
        predicted_fail = int(known.predicted_success.eq(0).sum())
        actual = None if actual_pass == actual_fail else int(actual_pass > actual_fail)
        predicted = None if predicted_pass == predicted_fail else int(predicted_pass > predicted_fail)
        rows.append(dict(zip(keys, key), total_runs=len(group), labeled_runs=len(known),
                         excluded_unlabeled_runs=len(group)-len(known),
                         actual_pass_votes=actual_pass, actual_fail_votes=actual_fail,
                         predicted_pass_votes=predicted_pass, predicted_fail_votes=predicted_fail,
                         actual_majority=actual, predicted_majority=predicted,
                         scored=actual is not None,
                         correct=bool(actual is not None and predicted is not None and actual == predicted)))
    table = pd.DataFrame(rows)
    if table.empty:
        raise ValueError('No cases available for majority voting')
    scored = table.loc[table.scored]
    tp = int((scored.actual_majority.eq(1) & scored.predicted_majority.eq(1)).sum())
    fp = int((scored.actual_majority.eq(0) & scored.predicted_majority.eq(1)).sum())
    positive = int(scored.actual_majority.eq(1).sum())
    negative = int(scored.actual_majority.eq(0).sum())
    tn = int((scored.actual_majority.eq(0) & scored.predicted_majority.eq(0)).sum())
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / positive if positive else 0.0
    metrics = dict(accuracy=float(scored.correct.mean()) if len(scored) else None,
                   balanced_accuracy=(0.5 * (recall + tn/negative) if positive and negative else None),
                   precision=precision, recall=recall,
                   f1=2*precision*recall/(precision+recall) if precision+recall else 0.0,
                   total_cases=len(table), scored_cases=len(scored),
                   correct_cases=int(scored.correct.sum()),
                   actual_tie_or_no_label_cases=int((~table.scored).sum()),
                   predicted_tie_scored_cases=int(scored.predicted_majority.isna().sum()),
                   definition='One vote per labeled run, one score per case. Actual ties are unscored; prediction ties count as incorrect.')
    return metrics, table


def case_runtime_metrics(frame, predictions, training_median_seconds, tolerance_percent=20):
    """Compare paired mean durations per case; each case has equal metric weight."""
    from train_runtime_predictor import evaluate_runtime_predictions

    predictions = np.asarray(predictions, dtype=float)
    if predictions.shape != (len(frame),) or not np.isfinite(predictions).all():
        raise ValueError('Expected one finite duration prediction per run')
    if (predictions < 0).any():
        raise ValueError('Predicted durations must be non-negative')
    durations = pd.to_numeric(frame['duration_s'], errors='raise')
    if np.isinf(durations).any() or durations.lt(0).any():
        raise ValueError('Actual durations must be non-negative and finite or missing')
    keys = ['debug_model', 'test_name'] if 'debug_model' in frame else ['test_name']
    values = frame[keys].copy()
    if values.isna().any(axis=None):
        raise ValueError('Case runtime metrics require non-missing case identifiers')
    values['actual'] = durations
    values['predicted'] = predictions
    rows = []
    for key, group in values.groupby(keys, sort=True):
        key = key if isinstance(key, tuple) else (key,)
        paired = group.loc[group.actual.notna() & group.actual.gt(0)]
        actual = float(paired.actual.mean()) if len(paired) else np.nan
        predicted = float(paired.predicted.mean()) if len(paired) else np.nan
        error = abs(actual-predicted)
        rows.append(dict(zip(keys, key), duration_runs=len(group),
                         valid_duration_runs=len(paired),
                         actual_mean_duration_s=actual, predicted_mean_duration_s=predicted,
                         actual_mean_duration_minutes=actual/60,
                         predicted_mean_duration_minutes=predicted/60,
                         actual_case_total_duration_s=float(paired.actual.sum()) if len(paired) else np.nan,
                         predicted_case_total_duration_s=float(paired.predicted.sum()) if len(paired) else np.nan,
                         absolute_mean_error_s=error,
                         absolute_mean_percentage_error=100*error/actual if actual > 0 else np.nan))
    table = pd.DataFrame(rows)
    if table.empty:
        raise ValueError('No cases available for duration evaluation')
    scored = table.dropna(subset=['actual_mean_duration_s'])
    metrics = evaluate_runtime_predictions(scored.actual_mean_duration_s.to_numpy(),
        scored.predicted_mean_duration_s.to_numpy(), training_median_seconds, tolerance_percent)
    metrics['scored_cases'] = metrics.pop('scored_rows')
    metrics['aggregation'] = 'Mean actual and predicted durations over the same positive-duration runs per case; each case weighted equally.'
    # Sums of case means are not the elapsed duration of all repeated runs.
    for name in ['total_actual_seconds', 'total_predicted_seconds',
                 'total_actual_minutes', 'total_predicted_minutes']:
        metrics.pop(name)
    metrics['total_actual_repeated_runs_minutes'] = float(scored.actual_case_total_duration_s.sum()/60)
    metrics['total_predicted_repeated_runs_minutes'] = float(scored.predicted_case_total_duration_s.sum()/60)
    return metrics, table
