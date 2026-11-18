import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from data_analysis import model_router_v0 as router
from test_discovery import match_pattern


def make_campaign(tmp_path: Path):
    registry = router.load_registry()
    cases = match_pattern("all")
    repo = tmp_path
    wave = repo / ".local" / "campaign"
    (wave / "plans").mkdir(parents=True)
    attempts = []
    models = [item["id"] for item in registry["candidates"]]
    for case in cases:
        config_dir = repo / "debug_assistant_latest" / "troubleshooting" / case
        config_dir.mkdir(parents=True)
        (config_dir / "config_step.json").write_text(
            json.dumps({"knowledge-prompt": {"problem-desc": f"Symptoms for {case}"}}),
            encoding="utf-8",
        )
        for replicate in range(1, 6):
            artifact_dir = wave / "plans" / router._slug(case)
            artifact_dir.mkdir(parents=True, exist_ok=True)
            plan_path = artifact_dir / f"plan_{replicate:03d}.txt"
            plan = f"Captured plan for {case}, replicate {replicate}"
            plan_path.write_text(plan, encoding="utf-8")
            response_hash = hashlib.sha256(plan.encode()).hexdigest()
            pair_id = f"{case}__plan_{replicate:03d}"
            for model_index, model in enumerate(models):
                unknown = case == cases[0] and replicate == 1 and model_index == 2
                success = None if unknown else ((cases.index(case) + replicate + model_index) % 3 != 0)
                mode = "capture" if model_index == 0 else "replay"
                attempts.append(
                    {
                        "attempt_key": f"{pair_id}__{model}",
                        "pair_id": pair_id,
                        "test_name": case,
                        "debug_model": model,
                        "mode": mode,
                        "exit_code": 0,
                        "ground_truth_after_debug_passed": success,
                        "ground_truth_passed": success,
                        "ground_truth_integrity_match": None if unknown else True,
                        "verifier_judgment": success,
                        "verifier_agrees_with_debug_ground_truth": None if unknown else True,
                        "source_knowledge_cost": 0.002 if mode == "capture" else None,
                        "shared_knowledge_cost_for_pair": 0.002,
                        "debug_cost": 0.01 * (model_index + 1),
                        "debug_input_tokens": 1000,
                        "debug_output_tokens": 100,
                        "debug_duration_s": 2.0 + model_index,
                        "response_sha256": response_hash,
                        "knowledge_prompt_sha256": hashlib.sha256(b"prompt").hexdigest(),
                    }
                )
    report = {
        "stop_reason": None,
        "attempt_count": len(attempts),
        "ground_truth_scored_attempts": sum(
            row["ground_truth_after_debug_passed"] is not None for row in attempts
        ),
        "recorded_provider_cost_usd": 9.0,
        "ground_truth_integrity_mismatches": 0,
        "campaign": {
            "campaign_id": "synthetic-router-unit-test",
            "cases": cases,
            "debug_models": models,
            "plan_replicates": 5,
        },
        "attempts": attempts,
    }
    report_path = wave / "campaign_report.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")
    return repo, report_path, report, registry, cases


def test_variants_cover_full_factorial_and_group_scenarios():
    variants = router.router_variants()
    assert len(variants) == 16
    assert len({item["name"] for item in variants}) == 16
    fold_map = router.scenario_folds(["a", "a", "b", "c", "d", "e"], folds=3, seed=7)
    assert set(fold_map) == {"a", "b", "c", "d", "e"}
    assert all(isinstance(value, int) and 0 <= value < 3 for value in fold_map.values())
    assert router.scenario_folds(["e", "d", "c", "b", "a"], folds=3, seed=7) == fold_map


def test_complete_campaign_preserves_unknown_ground_truth(tmp_path):
    repo, report_path, report, registry, cases = make_campaign(tmp_path)
    loaded, wave = router.validate_campaign(report_path, registry, repo_root=repo)
    observations = router.build_observations(loaded, wave, registry, repo_root=repo)
    assert len(observations) == len(cases) * 5
    first_model = registry["candidates"][2]["id"]
    assert observations[0]["candidates"][first_model]["success"] is None
    assert observations[0]["candidates"][first_model]["debug_cost_usd"] == pytest.approx(0.012)
    assert observations[0]["candidates"][first_model]["debug_cost_reported_usd"] == pytest.approx(0.03)
    priced = router._reprice_campaign(loaded, registry)
    assert priced["runner_recorded_provider_spend_usd"] == pytest.approx(9.0)
    assert priced["debug_token_count_missing_attempts"] == 0
    assert priced["registry_rate_debug_spend_estimate_usd"] > 0
    training = [item for item in observations if item["case"] != observations[0]["case"]]
    history = router._training_history(training, [item["id"] for item in registry["candidates"]])
    assert all("case" not in item and "pair_id" not in item for item in history)
    assert all(item["known_attempts"] == (len(cases) - 1) * 5 for item in history)


def test_campaign_rejects_inconsistent_pair_hashes(tmp_path):
    repo, report_path, report, registry, cases = make_campaign(tmp_path)
    report["attempts"][0]["response_sha256"] = "0" * 64
    report_path.write_text(json.dumps(report), encoding="utf-8")
    with pytest.raises(ValueError, match="response_sha256"):
        router.validate_campaign(report_path, registry, repo_root=repo)


def test_campaign_rejects_wrong_scenario_schedule(tmp_path):
    repo, report_path, report, registry, _ = make_campaign(tmp_path)
    report["campaign"]["plan_replicates"] = 3
    report_path.write_text(json.dumps(report), encoding="utf-8")
    with pytest.raises(ValueError, match="five independently captured"):
        router.validate_campaign(report_path, registry, repo_root=repo)


def test_ground_truth_boolean_validation_does_not_coerce_integer():
    with pytest.raises(ValueError, match="Invalid Ground Truth"):
        router._outcome({"ground_truth_after_debug_passed": 0})


def test_decisions_choice_parsing_and_request_shape():
    registry = router.load_registry()
    variant = next(item for item in router.router_variants() if item["router"] == "decisions")
    ids = {item["id"] for item in registry["candidates"]}
    response = {
        "model": "gpt-6-luna",
        "answers": [
            {
                "type": "choice",
                "name": "debug_agent",
                "choice": "gpt-6.2-sol",
                "probabilities": [{"value": "gpt-6.2-sol", "probability": 0.8}],
                "confidence": 0.8,
            }
        ],
        "usage": {"input_tokens": 100, "output_tokens": 0},
    }
    with patch.object(router, "_post_json", return_value=(response, "req-test")) as post:
        parsed, usage, request_id, resolved_model = router.call_router(
            variant, "private test prompt", registry, "test-key"
        )
    endpoint, body, _ = post.call_args.args
    assert endpoint == "decisions"
    assert body["model"] == "gpt-6-luna"
    assert body["questions"][0]["type"] == "choice"
    assert {item["value"] for item in body["questions"][0]["choices"]} == ids
    assert parsed["selected_model"] == "gpt-6.2-sol"
    assert usage["estimated_router_cost_usd"] == pytest.approx(0.00001)
    assert request_id == "req-test"
    assert resolved_model == "gpt-6-luna"


def test_responses_structured_choice_and_unknown_candidate_rejected():
    registry = router.load_registry()
    variant = next(item for item in router.router_variants() if item["router"] == "responses")
    response = {
        "model": "gpt-6-luna",
        "status": "completed",
        "output": [{"content": [{"type": "output_text", "text": '{"candidate":"gpt-6-luna"}'}]}],
        "usage": {"input_tokens": 100, "output_tokens": 10},
    }
    with patch.object(router, "_post_json", return_value=(response, "req-response")) as post:
        parsed, usage, request_id, _ = router.call_router(
            variant, "private test prompt", registry, "test-key"
        )
    endpoint, body, _ = post.call_args.args
    assert endpoint == "responses"
    assert body["text"]["format"]["strict"] is True
    assert body["text"]["format"]["schema"]["properties"]["candidate"]["enum"] == sorted(
        item["id"] for item in registry["candidates"]
    )
    assert parsed["selected_model"] == "gpt-6-luna"
    assert usage["estimated_router_cost_usd"] == pytest.approx(0.000015)
    assert request_id == "req-response"
    with pytest.raises(ValueError, match="invalid candidate"):
        router.parse_responses(
            {
                "status": "completed",
                "output": [{"content": [{"type": "output_text", "text": '{"candidate":"unknown"}'}]}],
            },
            {"gpt-6-luna"},
        )


def test_decisions_refusal_is_not_a_successful_selection():
    with pytest.raises(ValueError, match="refused"):
        router.parse_decisions(
            {"answers": [{"type": "refusal", "name": "debug_agent"}]},
            {"gpt-6-luna"},
        )



def test_score_rows_keeps_unknown_outcomes_out_of_success_denominator():
    score = router._score_rows(
        [
            {"case": "a", "success": True, "pipeline_cost_usd": 0.1},
            {"case": "a", "success": None, "pipeline_cost_usd": 0.2},
            {"case": "b", "success": False, "pipeline_cost_usd": 0.3},
        ],
        total=4,
        label="test",
        bootstrap_replicates=50,
    )
    assert score["routed_attempts"] == 3
    assert score["route_failure_attempts"] == 1
    assert score["router_decision_coverage"] == pytest.approx(3 / 4)
    assert score["known_ground_truth_attempts"] == 2
    assert score["unknown_ground_truth_attempts"] == 1
    assert score["ground_truth_coverage"] == pytest.approx(2 / 3)
    assert score["pooled_ground_truth_success_rate"] == pytest.approx(0.5)



def test_report_creates_private_aggregate_figures_without_raw_inputs(tmp_path, monkeypatch):
    repo, report_path, source_report, registry, _ = make_campaign(tmp_path)
    loaded, wave = router.validate_campaign(report_path, registry, repo_root=repo)
    observations = router.build_observations(loaded, wave, registry, repo_root=repo)
    monkeypatch.setattr(router, "REPO_ROOT", repo)
    variants = router.router_variants()
    events = []
    for observation in observations:
        for variant in variants:
            selected = registry["candidates"][0]["id"]
            event = {
                "event": "router_finished",
                "route_id": f"{observation['pair_id']}::{variant['name']}",
                "pair_id": observation["pair_id"],
                "scenario": observation["case"],
                "variant": variant["name"],
                "status": "success",
                "selected_model": selected,
                "choice_probabilities": {selected: 0.8},
                "choice_confidence": 0.8,
                "estimated_router_cost_usd": 0.0001,
                "latency_s": 0.2,
            }
            if not events:
                event["status"] = "invalid_response"
                event["error_code"] = "responses_router_refused"
                event.pop("selected_model")
                event.pop("choice_probabilities")
                event.pop("choice_confidence")
            events.append(event)
    out = repo / ".local" / "router-output"
    result = router.write_report(
        out,
        observations,
        events,
        registry,
        source_report,
        bootstrap_replicates=50,
    )
    assert result["router_decision_count"] == 16 * len(observations) - 1
    assert result["invalid_router_response_count"] == 1
    first_policy = result["router_policies"][0]
    assert first_policy["router_decision_coverage"] == pytest.approx((len(observations) - 1) / len(observations))
    assert first_policy["router_requests_attempted"] == len(observations)
    assert first_policy["total_router_cost_usd"] == pytest.approx(0.0001 * len(observations))
    assert len(result["figures"]) == 4
    assert (out / "router_report.json").stat().st_mode & 0o777 == 0o600
    assert (out / "figures").stat().st_mode & 0o777 == 0o700
    rendered = (out / "router_report.json").read_text()
    assert "Symptoms for" not in rendered
    assert "Captured plan for" not in rendered
