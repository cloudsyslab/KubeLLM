#!/usr/bin/env python3
"""Automation script: runs test cases with multiple models until success or all exhausted.

Supports two MAB modes:
- Stationary MAB (--no-feedback): Each model sees only knowledge agent's plan (fixed success probability per model)
- Non-stationary MAB (--include-feedback, default): Each model sees knowledge plan + feedback from previous attempts (success probability can change)
"""

import os
import re
from pathlib import Path
from main import allStepsAtOnce, allStepsAtOnceWithoutKnowledgeAgent
from metrics_db import store_attempt_context, get_latest_attempt_context, clear_attempt_context

DEFAULT_MODELS = ["gpt-5-nano", "gpt-5-mini", "gpt-4o-mini", "gpt-4o"]

# Tokens agents use; regex to extract verdict + reasoning before it
DEBUG_TOKENS_RE = re.compile(r"(.{0,500})(<\|SOLVED\|>|<\|FAILED\|>|<\|ERROR\|>)", re.DOTALL)
VERIFICATION_TOKENS_RE = re.compile(r"(.{0,350})(<\|VERIFIED\|>|<\|FAILED\|>|<\|VERIFICATION_ERROR\|>)\s*$", re.DOTALL)


def _extract_debug_excerpt(text, max_fallback=500):
    """Extract reasoning + verdict from debug response using regex (last occurrence of token)."""
    if not (text or "").strip():
        return ""
    text = text.strip()
    matches = list(DEBUG_TOKENS_RE.finditer(text))
    if matches:
        m = matches[-1]
        excerpt = (m.group(1) + m.group(2)).strip()
        return excerpt if len(excerpt) <= max_fallback + 50 else "..." + excerpt[-max_fallback:]
    return text[-max_fallback:] if len(text) > max_fallback else text


def _extract_verification_excerpt(text, max_fallback=400):
    """Extract reasoning + verdict from verification report (token at end)."""
    if not (text or "").strip():
        return ""
    text = text.strip()
    m = VERIFICATION_TOKENS_RE.search(text)
    if m:
        return (m.group(1) + m.group(2)).strip()
    return text[-max_fallback:] if len(text) > max_fallback else text


def build_attempt_summary(debug_response, verification_report, model_used, max_debug_chars=500, max_verification_chars=400):
    """Build a short bounded summary of a failed attempt for the next model.
    Uses regex to extract verdict tokens and the reasoning just before them."""
    if not debug_response and not verification_report:
        return f"Previous attempt (model: {model_used}) did not resolve the issue."
    parts = [f"Previous attempt (model: {model_used}) did not resolve the issue."]
    if debug_response:
        s = _extract_debug_excerpt(debug_response, max_fallback=max_debug_chars)
        if s:
            parts.append("What was done: " + s)
    if verification_report:
        s = _extract_verification_excerpt(verification_report, max_fallback=max_verification_chars)
        if s:
            parts.append("Verification outcome: " + s)
    return "\n".join(parts)


def teardown_environment(test_name):
    """Teardown the environment for a test case using Python function from kube_test."""
    try:
        from kube_test import tearDownEnviornment
        tearDownEnviornment(test_name)
        print(f"  Teardown completed")
        return True
    except ImportError:
        print(f"  Warning: Could not import kube_test.tearDownEnviornment")
        return False
    except Exception as e:
        print(f"  Warning: Teardown failed: {e}")
        return False

def get_test_cases(troubleshooting_dir):
    """Get all test cases from troubleshooting directory."""
    test_cases = []
    for test_dir in Path(troubleshooting_dir).iterdir():
        if test_dir.is_dir():
            config_file = test_dir / "config_step.json"
            if config_file.exists():
                test_cases.append({"name": test_dir.name, "config_path": str(config_file)})
    return test_cases

def run_automation_suite(troubleshooting_dir=None, models=None, temperature=None, test_cases=None, test_mode="allStepsAtOnce", include_feedback=True):
    """Run test cases with multiple models until success or all exhausted.
    
    Note: Only 'allStepsAtOnce' mode is supported as verification agent only works with this mode.
    Temperature is only changed if explicitly provided via --temperature argument.
    
    Args:
        include_feedback: If True (default), next debug agent sees knowledge plan + feedback from previous attempts (non-stationary MAB).
                         If False, next debug agent sees ONLY knowledge plan (stationary MAB - fixed success probability per model).
    """
    if test_mode != "allStepsAtOnce":
        raise ValueError(f"Automation only supports 'allStepsAtOnce' mode. Verification agent requires this mode. Got: {test_mode}")
    
    troubleshooting_dir = troubleshooting_dir or os.path.expanduser("~/KubeLLM/debug_assistant_latest/troubleshooting")
    models = models or DEFAULT_MODELS
    
    if test_cases is None:
        test_cases = get_test_cases(troubleshooting_dir)
    else:
        test_cases = [{"name": tc, "config_path": os.path.join(troubleshooting_dir, tc, "config_step.json")} for tc in test_cases]
    
    for test_case in test_cases:
        test_name = test_case["name"]
        config_path = test_case["config_path"]
        
        if not os.path.exists(config_path):
            continue
        
        print(f"\n{'='*80}\nTEST: {test_name}\n{'='*80}")
        
        # Clear any old context for this test case (fresh start)
        db_path = os.path.expanduser("~/KubeLLM/token_metrics.db")
        clear_attempt_context(db_path, test_name)
        
        # Run knowledge agent once
        # Use temperature override if provided, otherwise uses config default
        try:
            result = allStepsAtOnce(config_path, model_override=None, temperature_override=temperature)
            knowledge_response = result.get("knowledge_response")
            if result.get("verification_status"):
                print(f"[SUCCESS] {test_name} succeeded")
                clear_attempt_context(db_path, test_name)  # Clear context on success
                continue
            else:
                # First attempt failed; build short summary, store in DB, then teardown
                last_attempt_summary = build_attempt_summary(
                    result.get("debug_response", ""),
                    result.get("verification_report", ""),
                    result.get("debug_model_used", "unknown"),
                )
                # Store context in DB for next model iteration (always store, but may not use if --no-feedback)
                store_attempt_context(db_path, test_name, result.get("debug_model_used", "unknown"), last_attempt_summary)
                mode_str = "non-stationary MAB" if include_feedback else "stationary MAB"
                print(f"  First attempt failed, context stored in DB ({mode_str} mode), tearing down environment...")
                teardown_environment(test_name)
        except Exception as e:
            print(f"Error: {e}")
            # Teardown even if there was an error
            print(f"  Tearing down environment after error...")
            teardown_environment(test_name)
            continue

        # Try different models if first attempt failed
        # Temperature is only used if explicitly provided, otherwise uses config/default
        for model in models:
            print(f"Trying {model}...")
            # Retrieve context from DB only if include_feedback is True (for non-stationary MAB)
            # If False (stationary MAB), next agent sees only knowledge plan (no feedback)
            last_attempt_summary = None
            if include_feedback:
                last_attempt_summary = get_latest_attempt_context(db_path, test_name)
                if last_attempt_summary:
                    print(f"  Retrieved context from DB for previous attempt (non-stationary MAB mode)")
            else:
                print(f"  Using only knowledge plan (stationary MAB mode - no feedback from previous attempts)")
            
            try:
                result = allStepsAtOnceWithoutKnowledgeAgent(
                    config_path, knowledge_response, model, temperature,
                    previous_attempt_summary=last_attempt_summary,
                )
                if result.get("verification_status"):
                    print(f"[SUCCESS] {test_name} succeeded with {model}")
                    clear_attempt_context(db_path, test_name)  # Clear context on success
                    break
                else:
                    # Build short summary, store in DB for next model (only if include_feedback is True)
                    # Even if not used immediately, storing allows switching modes mid-run
                    last_attempt_summary = build_attempt_summary(
                        result.get("debug_response", ""),
                        result.get("verification_report", ""),
                        result.get("debug_model_used", "unknown"),
                    )
                    # Always store context in DB (allows switching between stationary/non-stationary modes)
                    store_attempt_context(db_path, test_name, result.get("debug_model_used", "unknown"), last_attempt_summary)
                    if include_feedback:
                        print(f"  Attempt with {model} failed, context stored in DB, tearing down environment...")
                    else:
                        print(f"  Attempt with {model} failed (context stored but not used in stationary mode), tearing down environment...")
                    teardown_environment(test_name)
            except Exception as e:
                print(f"Error: {e}")
                # Teardown even if there was an error
                print(f"  Tearing down environment after error...")
                teardown_environment(test_name)
        else:
            print(f"[FAILED] {test_name} failed after trying all models")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Automation script for running test cases with multiple models. Only supports 'allStepsAtOnce' mode.")
    parser.add_argument("--troubleshooting-dir", type=str, help="Path to troubleshooting directory")
    parser.add_argument("--models", nargs="+", help="List of models to try (default: gpt-5-nano, gpt-5-mini, gpt-4o-mini, gpt-4o)")
    parser.add_argument("--temperature", type=float, help="Temperature to use for all attempts (if not provided, uses config file default)")
    parser.add_argument("--test-cases", nargs="+", help="Specific test cases to run")
    parser.add_argument("--test-mode", type=str, default="allStepsAtOnce", 
                       help="Test mode (default: allStepsAtOnce). Only 'allStepsAtOnce' is supported as verification requires this mode.")
    parser.add_argument("--include-feedback", action="store_true", default=True,
                       help="Include feedback from previous attempts (default: True). Non-stationary MAB - success probability can change.")
    parser.add_argument("--no-feedback", dest="include_feedback", action="store_false",
                       help="Do NOT include feedback from previous attempts. Stationary MAB - fixed success probability per model.")
    args = parser.parse_args()
    
    if args.test_mode != "allStepsAtOnce":
        print(f"Error: Automation only supports 'allStepsAtOnce' mode.")
        print(f"Verification agent only works with 'allStepsAtOnce' mode.")
        print(f"Received: {args.test_mode}")
        exit(1)
    
    run_automation_suite(args.troubleshooting_dir, args.models, args.temperature, args.test_cases, args.test_mode, args.include_feedback)

