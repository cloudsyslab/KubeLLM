# Prediction selector harness pilot

This is the sanitized export of campaign `pilot-v1-warmup-v2`. It checks the
paired-run harness and records early direction for the offline
post-KnowledgeAgent DebugAgent selector. It is not a predictor-quality or
generalization result, and it does not enable live routing.

## Results

The schedule covered three cases, two KnowledgeAgent plans per case, and
three DebugAgent candidates: 18 planned attempts. The campaign finished 14;
13 have post-debug Ground Truth, with 12 passes and one failure. One attempt
ended before Ground Truth after a runtime HTTP 500/XML parsing error; its
outcome remains unknown. The terminal campaign contains four unstarted
attempts. It was not retried or resumed. The backend cause of the runtime
error has not been established.

Ground Truth before and after Verification matched on all 13 scored attempts.
The three candidate observed rates are based on incomplete and uneven task
coverage. No fully observed static model met the 80%, 90%, 95%, or 100%
equal-task thresholds. Do not treat observed 100% rates on partial coverage as
a guarantee or as evidence that one model is generally better.

Recorded provider spend was $0.0725. Modeled selected-pipeline spend was
$0.1394, allocating the shared KnowledgeAgent call to each candidate policy.
GPU hosting cost was not priced. See `campaign_summary.json` and
`attempts.csv` for candidate and attempt-level counts, outcomes, costs, timing,
warm-up status, and the categorical stop reason.

## Privacy and reproduction

Raw prompts, responses, commands, logs, lane details, and free-form runtime
errors remain in ignored local campaign output. The exporter includes only
reviewed case/model IDs, categorical statuses, Ground Truth and verifier
labels, numeric costs and durations, and aggregate metrics. It omits run paths,
prompt text, tool output, response content, hashes, and raw stop text.

Regenerate this pack from the private report with:

```bash
python3 data_analysis/export_prediction_pilot.py \
  --source-report .local/prediction_campaigns/pilot-v1-warmup-v2/campaign_report.json
```

The exporter refuses to overwrite a nonempty destination and checks that the
projected attempt count and recorded provider costs reconcile with the source
report.
