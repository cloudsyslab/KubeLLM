import hashlib
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from data_analysis.run_paired_campaign import (
    MINIMUM_ATTEMPT_FREE_BYTES,
    MINIMUM_STARTUP_FREE_BYTES,
    PILOT_MAX_SCHEDULED_ATTEMPTS,
    PILOT_STARTUP_FREE_BYTES,
    RUNNER,
    _build_command,
    _candidate_orders,
    _cost_success_frontier,
    _model_summary,
    _active_debug_phase_elapsed_s,
    _load_attempts,
    _attempt_disk_stop_reason,
    _startup_disk_error,
    _storage_policy,
    _startup_minimum_free_bytes,
    _write_report,
    _validate_recovery_record,
    _summary_indicates_debug_agent_timeout,
    _debug_timeout_has_scored_ground_truth,
    _validate_initial_campaign_root,
    _tier_fit,
    _paired_routing_potential,
)


class PairedCampaignTests(unittest.TestCase):
    def test_debug_agent_timeout_requires_primary_ground_truth_and_clean_teardown_to_continue(self):
        summary = {
            "status": "ERROR",
            "error_message": "Error asking question to debug agent: 'Timed Out'",
            "error_context": "Traceback from debug_assistant_latest/debug_agents.py",
        }
        self.assertTrue(_summary_indicates_debug_agent_timeout(summary))
        self.assertFalse(_summary_indicates_debug_agent_timeout({"error_message": "API request timeout"}))
        self.assertFalse(_summary_indicates_debug_agent_timeout(None))

        result = {
            "debug_agent_timed_out": True,
            "ground_truth_after_debug_passed": False,
            "teardown_status": "passed",
        }
        self.assertTrue(_debug_timeout_has_scored_ground_truth(result))
        result["teardown_status"] = "failed"
        self.assertFalse(_debug_timeout_has_scored_ground_truth(result))
        result["teardown_status"] = "passed"
        result["ground_truth_after_debug_passed"] = None
        self.assertFalse(_debug_timeout_has_scored_ground_truth(result))

    def test_active_debug_phase_elapsed_uses_latest_heartbeat_until_phase_end(self):
        with TemporaryDirectory() as directory:
            run_dir = Path(directory)
            task_dir = run_dir / "case-a"
            task_dir.mkdir()
            progress = task_dir / "progress.log"
            events = [
                {"event": "phase_start", "phase": "debug"},
                {"event": "phase_heartbeat", "phase": "debug", "elapsed_s": 481.25},
                {"event": "phase_start", "phase": "verification"},
            ]
            progress.write_text("".join(json.dumps(event) + "\n" for event in events), encoding="utf-8")
            self.assertEqual(_active_debug_phase_elapsed_s(run_dir, "case-a"), 481.25)
            with progress.open("a", encoding="utf-8") as stream:
                stream.write('{"event":"phase_heartbeat","phase":"debug","elapsed_s":490')
            self.assertEqual(_active_debug_phase_elapsed_s(run_dir, "case-a"), 481.25)
            with progress.open("a", encoding="utf-8") as stream:
                stream.write("}\n" + json.dumps({"event": "phase_end", "phase": "debug"}) + "\n")
            self.assertIsNone(_active_debug_phase_elapsed_s(run_dir, "case-a"))
            self.assertIsNone(_active_debug_phase_elapsed_s(run_dir, "case-a"))

    def test_reconciliation_event_overlays_outcome_without_rewriting_finished_event(self):
        rows, completed, started = _load_attempts([
            {"event": "attempt_started", "attempt_key": "case-a__model-x"},
            {"event": "attempt_finished", "attempt_key": "case-a__model-x", "exit_code": -15},
            {
                "event": "attempt_outcome_reconciled",
                "attempt_key": "case-a__model-x",
                "overrides": {"status": "TIMEOUT", "ground_truth_passed": False},
                "reconciliation": {"artifact": "ground_truth.json"},
            },
        ])
        self.assertEqual(completed, {"case-a__model-x"})
        self.assertEqual(started, set())
        self.assertEqual(rows[0]["exit_code"], -15)
        self.assertEqual(rows[0]["status"], "TIMEOUT")
        self.assertFalse(rows[0]["ground_truth_passed"])
        self.assertTrue(rows[0]["outcome_reconciled"])

    def test_retry_authorization_reopens_only_the_failed_attempt_key(self):
        key = "case-a__plan_001__model-x"
        events = [
            {"event": "attempt_started", "attempt_key": key},
            {"event": "attempt_finished", "attempt_key": key, "status": "ERROR", "exit_code": 1},
            {"event": "attempt_retry_authorized", "attempt_key": key, "reason": "dependency mismatch"},
        ]
        rows, completed, started = _load_attempts(events)
        self.assertEqual(rows, [])
        self.assertNotIn(key, completed)
        self.assertNotIn(key, started)
        events.extend([
            {"event": "attempt_started", "attempt_key": key},
            {"event": "attempt_finished", "attempt_key": key, "status": "PASS", "exit_code": 0},
        ])
        rows, completed, started = _load_attempts(events)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["status"], "PASS")
        self.assertEqual(completed, {key})
        self.assertEqual(started, set())

    def test_retry_authorization_requires_a_prior_finished_attempt(self):
        with self.assertRaisesRegex(ValueError, "does not match a completed attempt"):
            _load_attempts([{"event": "attempt_retry_authorized", "attempt_key": "missing"}])

    def test_incomplete_cost_recording_is_not_reported_as_zero(self):
        rows = [
            {
                "debug_model": "model-a",
                "test_name": "case-a",
                "ground_truth_passed": True,
                "effective_cost_with_shared_knowledge_call": 2.0,
                "api_cost": 0.5,
                "debug_cost": 1.0,
                "verification_cost": 0.5,
                "cost_recording_complete": True,
            },
            {
                "debug_model": "model-a",
                "test_name": "case-a",
                "ground_truth_passed": False,
                "effective_cost_with_shared_knowledge_call": None,
                "api_cost": None,
                "debug_cost": None,
                "verification_cost": None,
                "cost_recording_complete": False,
            },
        ]
        config = {
            "campaign_id": "cost-test",
            "cases": ["case-a"],
            "plan_replicates": 2,
            "gpu_cost_assumptions": {},
            "disk_guard": {
                "profile": "standard",
                "minimum_startup_free_bytes": MINIMUM_STARTUP_FREE_BYTES,
                "minimum_before_attempt_free_bytes": MINIMUM_ATTEMPT_FREE_BYTES,
                "maximum_scheduled_attempts": None,
            },
        }
        with TemporaryDirectory() as directory:
            root = Path(directory)
            _write_report(root, config, rows, ["model-a"], None)
            report = json.loads((root / "campaign_report.json").read_text(encoding="utf-8"))
            markdown = (root / "campaign_report.md").read_text(encoding="utf-8")
        candidate = report["candidate_summary"][0]
        self.assertFalse(candidate["cost_recording_complete"])
        self.assertIsNone(candidate["mean_effective_cost_with_shared_knowledge_call"])
        self.assertIsNone(candidate["total_effective_cost_with_shared_knowledge_call"])
        self.assertEqual(report["recorded_provider_cost_usd"], 2.0)
        self.assertEqual(report["cost_recording_incomplete_attempts"], 1)
        self.assertFalse(report["recorded_provider_cost_complete"])
        self.assertIn("incomplete attempt costs: 1", markdown)

    def test_storage_guard_enforces_startup_and_between_attempt_floors(self):
        self.assertIsNone(_startup_disk_error(MINIMUM_STARTUP_FREE_BYTES))
        self.assertIn(
            "20.00 GB required",
            _startup_disk_error(MINIMUM_STARTUP_FREE_BYTES - 1),
        )
        self.assertIsNone(_startup_disk_error(PILOT_STARTUP_FREE_BYTES, PILOT_STARTUP_FREE_BYTES))
        self.assertIn(
            "12.00 GB required",
            _startup_disk_error(PILOT_STARTUP_FREE_BYTES - 1, PILOT_STARTUP_FREE_BYTES),
        )
        self.assertIsNone(_attempt_disk_stop_reason(MINIMUM_ATTEMPT_FREE_BYTES, "attempt-2"))
        self.assertIn(
            "attempt-2",
            _attempt_disk_stop_reason(MINIMUM_ATTEMPT_FREE_BYTES - 1, "attempt-2"),
        )

    def test_resuming_campaign_uses_per_attempt_floor_without_weakening_new_start(self):
        policy = _storage_policy(False, 540)
        self.assertEqual(_startup_minimum_free_bytes(policy, resume=False), MINIMUM_STARTUP_FREE_BYTES)
        self.assertEqual(_startup_minimum_free_bytes(policy, resume=True), MINIMUM_ATTEMPT_FREE_BYTES)
        self.assertIsNone(_startup_disk_error(19_800_000_000, _startup_minimum_free_bytes(policy, resume=True)))

    def test_pilot_storage_policy_is_explicit_and_capped(self):
        standard = _storage_policy(False, 486)
        pilot = _storage_policy(True, PILOT_MAX_SCHEDULED_ATTEMPTS)

        self.assertEqual(standard["profile"], "standard")
        self.assertEqual(standard["minimum_startup_free_bytes"], MINIMUM_STARTUP_FREE_BYTES)
        self.assertIsNone(standard["maximum_scheduled_attempts"])
        self.assertEqual(pilot["profile"], "pilot_18")
        self.assertEqual(pilot["minimum_startup_free_bytes"], PILOT_STARTUP_FREE_BYTES)
        self.assertEqual(pilot["minimum_before_attempt_free_bytes"], MINIMUM_ATTEMPT_FREE_BYTES)
        self.assertEqual(pilot["maximum_scheduled_attempts"], PILOT_MAX_SCHEDULED_ATTEMPTS)
        with self.assertRaisesRegex(ValueError, "limited to 18 scheduled candidate attempts"):
            _storage_policy(True, PILOT_MAX_SCHEDULED_ATTEMPTS + 1)

    def test_recovery_record_is_bound_to_stop_reason_lane_and_attempt_ledger(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            events = root / "attempts.jsonl"
            events.write_text('{"event":"attempt_finished","attempt_key":"case-a"}\n', encoding="utf-8")
            record = {
                "schema_version": 1,
                "campaign_id": "campaign-a",
                "prior_stop_reason": "fixture teardown failed",
                "resolved_cause": "selected lane teardown completed",
                "lane_fingerprint": "lane-sha",
                "preflight_passed": True,
                "teardown_completed": True,
                "attempt_ledger_sha256": hashlib.sha256(events.read_bytes()).hexdigest(),
                "verified_at_utc": "2026-11-21T23:30:00Z",
            }
            recovery = root / "recovery.json"
            recovery.write_text(json.dumps(record), encoding="utf-8")
            parsed, digest = _validate_recovery_record(
                recovery,
                campaign_id="campaign-a",
                stop_reason="fixture teardown failed",
                events_path=events,
                lane_fingerprint="lane-sha",
            )
            self.assertEqual(parsed, record)
            self.assertEqual(digest, hashlib.sha256(recovery.read_bytes()).hexdigest())
            with self.assertRaisesRegex(ValueError, "recorded stop reason"):
                _validate_recovery_record(
                    recovery,
                    campaign_id="campaign-a",
                    stop_reason="different stop reason",
                    events_path=events,
                    lane_fingerprint="lane-sha",
                )
            events.write_text(events.read_text(encoding="utf-8") + " ", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Attempt ledger changed"):
                _validate_recovery_record(
                    recovery,
                    campaign_id="campaign-a",
                    stop_reason="fixture teardown failed",
                    events_path=events,
                    lane_fingerprint="lane-sha",
                )

    def test_report_records_storage_headroom_for_each_attempt(self):
        config = {
            "campaign_id": "storage-test",
            "cases": ["case-a"],
            "plan_replicates": 1,
            "gpu_cost_assumptions": {},
            "disk_guard": {
                "profile": "pilot_18",
                "minimum_startup_free_bytes": MINIMUM_STARTUP_FREE_BYTES,
                "minimum_before_attempt_free_bytes": MINIMUM_ATTEMPT_FREE_BYTES,
                "maximum_scheduled_attempts": PILOT_MAX_SCHEDULED_ATTEMPTS,
            },
        }
        attempt = {
            "debug_model": "model-a",
            "test_name": "case-a",
            "ground_truth_passed": True,
            "effective_cost_with_shared_knowledge_call": 1.0,
            "storage_free_before_bytes": MINIMUM_STARTUP_FREE_BYTES,
            "storage_free_after_bytes": MINIMUM_ATTEMPT_FREE_BYTES,
        }
        with TemporaryDirectory() as directory:
            root = Path(directory)
            _write_report(root, config, [attempt], ["model-a"], None)
            report = (root / "campaign_report.json").read_text(encoding="utf-8")
            markdown = (root / "campaign_report.md").read_text(encoding="utf-8")

        self.assertIn('"storage_free_before_bytes": 20000000000', report)
        self.assertIn('"storage_free_after_bytes": 10000000000', report)
        self.assertIn("## Storage measurements", markdown)
        self.assertIn("20.00 GB", markdown)
        self.assertIn("10.00 GB", markdown)

    def test_summary_reports_pooled_and_equal_task_success_and_full_shared_cost(self):
        rows = [
            {
                "debug_model": "model-a",
                "test_name": "case-a",
                "ground_truth_passed": True,
                "effective_cost_with_shared_knowledge_call": 3.0,
            },
            {
                "debug_model": "model-a",
                "test_name": "case-a",
                "ground_truth_passed": False,
                "effective_cost_with_shared_knowledge_call": 6.0,
            },
            {
                "debug_model": "model-a",
                "test_name": "case-b",
                "ground_truth_passed": True,
                "effective_cost_with_shared_knowledge_call": 9.0,
            },
            {
                "debug_model": "model-a",
                "test_name": "case-c",
                "ground_truth_passed": None,
                "effective_cost_with_shared_knowledge_call": 12.0,
            },
        ]

        summary = _model_summary(rows, ["model-a", "model-b"])
        self.assertEqual(summary[0]["attempts_with_ground_truth"], 3)
        self.assertAlmostEqual(summary[0]["pooled_ground_truth_success_rate"], 2 / 3)
        self.assertAlmostEqual(summary[0]["equal_task_ground_truth_success_rate"], 0.75)
        self.assertAlmostEqual(summary[0]["mean_effective_cost_with_shared_knowledge_call"], 7.5)
        # Failed and unknown attempts still consumed their full pipeline cost.
        self.assertAlmostEqual(summary[0]["mean_effective_cost_per_success"], 15.0)
        self.assertAlmostEqual(summary[0]["total_effective_cost_with_shared_knowledge_call"], 30.0)
        self.assertEqual(summary[1]["attempts_with_ground_truth"], 0)

    def test_command_uses_canonical_runner_and_capture_replay_flag(self):
        command = _build_command(
            test_name="port_mismatch",
            debug_model="candidate-z",
            run_dir=Path("/tmp/campaign/run-1"),
            artifact_path=Path("/tmp/campaign/plan.txt"),
            mode="replay",
            api_model="fixed-api",
            verification_model="fixed-verifier",
            lab_config=Path("/tmp/private-lane.json"),
            ollama_num_ctx=8192,
        )
        self.assertEqual(Path(command[1]), RUNNER)
        self.assertIn("candidate-z", command)
        self.assertIn("--replay-knowledge-response", command)
        self.assertIn("fixed-api", command)
        self.assertIn("fixed-verifier", command)
        self.assertIn(str(Path("/tmp/private-lane.json").resolve()), command)
        self.assertIn("--ollama-debug-num-ctx", command)
        self.assertIn("8192", command)

    def test_local_candidate_command_opts_into_debug_entry_warmup(self):
        command = _build_command(
            test_name="port_mismatch",
            debug_model="glm-4.7-flash:latest",
            run_dir=Path("/tmp/campaign/run-2"),
            artifact_path=Path("/tmp/campaign/plan.txt"),
            mode="replay",
            api_model=None,
            verification_model=None,
            lab_config=None,
            warmup_digest="a" * 64,
            warmup_allow_models=["glm-4.7-flash:latest", "nemotron-cascade-2:30b"],
            warmup_keep_alive="10m",
        )

        self.assertIn("--ollama-debug-warmup", command)
        self.assertIn("--ollama-debug-warmup-digest", command)
        self.assertIn("a" * 64, command)
        self.assertIn("glm-4.7-flash:latest,nemotron-cascade-2:30b", command)
        self.assertIn("10m", command)

    def test_cost_frontier_requires_complete_ground_truth_coverage(self):
        rows = [
            {
                "debug_model": "cheap",
                "test_name": "case-a",
                "ground_truth_passed": True,
                "effective_cost_with_shared_knowledge_call": 1.0,
            },
            {
                "debug_model": "cheap",
                "test_name": "case-b",
                "ground_truth_passed": None,
                "effective_cost_with_shared_knowledge_call": 1.0,
            },
            {
                "debug_model": "reliable",
                "test_name": "case-a",
                "ground_truth_passed": True,
                "effective_cost_with_shared_knowledge_call": 4.0,
            },
            {
                "debug_model": "reliable",
                "test_name": "case-b",
                "ground_truth_passed": True,
                "effective_cost_with_shared_knowledge_call": 4.0,
            },
        ]
        summary = _model_summary(rows, ["cheap", "reliable"], ["case-a", "case-b"], 1)
        frontier = _cost_success_frontier(summary, thresholds=(0.8, 1.0))
        self.assertEqual(frontier[0]["lowest_mean_cost_model"], "reliable")
        self.assertEqual(frontier[1]["lowest_mean_cost_model"], "reliable")

    def test_candidate_capture_order_is_balanced_and_deterministic(self):
        cases = ["case-a", "case-b"]
        models = ["model-a", "model-b", "model-c"]
        first = _candidate_orders(cases, 3, models, 17)
        second = _candidate_orders(cases, 3, models, 17)
        self.assertEqual(first, second)
        self.assertEqual(
            {order[0] for order in first.values()},
            set(models),
        )
        self.assertTrue(all(set(order) == set(models) for order in first.values()))

    def test_local_tier_fit_uses_private_ollama_process_vram(self):
        model = "gemma4:e4b-it-q4_K_M"
        reported_api_vram = 313_775_881
        process_vram = 4_783 * 1024**2
        fit = _tier_fit(
            model,
            {
                "status": "ok",
                "models": [{
                    "name": model,
                    "size_bytes": reported_api_vram,
                    "size_vram_bytes": reported_api_vram,
                    "gpu_residency_fraction": 1.0,
                }],
            },
            {
                "ollama_gpu_process_peak_bytes_by_model": {model: process_vram},
                "peak_used_mib": 4_803,
                "peak_delta_mib": 4_803,
            },
        )
        self.assertEqual(fit["model_gpu_bytes"], process_vram)
        self.assertEqual(fit["ollama_reported_gpu_bytes"], reported_api_vram)
        self.assertEqual(fit["measurement_source"], "nvidia-smi compute-app memory scoped to the selected private Ollama server")
        self.assertTrue(fit["within_vram_budget"])
        self.assertEqual(fit["gpu_residency_fraction"], 1.0)

    def test_paired_routing_report_handles_a_complete_four_model_pair(self):
        models = ["gpt-5-nano", "gpt-6-luna", "gemma4:e4b-it-q4_K_M", "qwen3.5:9b-q4_K_M"]
        pair_id = "case-a__plan_001"
        rows = [
            {
                "pair_id": pair_id,
                "test_name": "case-a",
                "debug_model": model,
                "ground_truth_passed": model in {"gpt-5-nano", "gemma4:e4b-it-q4_K_M"},
            }
            for model in models
        ]
        result = _paired_routing_potential(rows, models, {pair_id: "usable"})
        all_pairs = result["all_reviewed_and_unreviewed_pairs"]
        self.assertEqual(all_pairs["complete_all_model_pairs"], 1)
        self.assertEqual(all_pairs["outcome_patterns"], {"model_outcomes_differ": 1})
        self.assertEqual(result["by_plan_review_label"]["usable"]["complete_all_model_pairs"], 1)

    def test_initial_campaign_accepts_only_known_pre_run_evidence(self):
        with TemporaryDirectory() as directory:
            root = Path(directory) / "campaign"
            _validate_initial_campaign_root(root)
            root.mkdir()
            _validate_initial_campaign_root(root)
            for name in (
                "plan_review.jsonl",
                "plan_review_summary.json",
                "lab_cleanup_manifest.json",
            ):
                (root / name).write_text("{}\n", encoding="utf-8")
            _validate_initial_campaign_root(root)
            (root / "unexpected.log").write_text("raw data\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unexpected.log"):
                _validate_initial_campaign_root(root)



if __name__ == "__main__":
    unittest.main()
