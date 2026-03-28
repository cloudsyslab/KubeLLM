"""
Compare two KubeLLM test run directories using aggregate.json and per-test summary.json files.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent


def resolve_run_dir(arg: str) -> Path:
    """Resolve a run directory from an absolute path or a timestamp id under .local/test_runs/."""
    p = Path(arg)
    if p.is_dir():
        return p.resolve()
    candidate = REPO_ROOT / ".local" / "test_runs" / arg
    if candidate.is_dir():
        return candidate.resolve()
    raise FileNotFoundError(f"Run directory not found: {arg}")


def load_aggregate(run_dir: Path) -> Dict[str, Any]:
    path = run_dir / "aggregate.json"
    if not path.exists():
        raise FileNotFoundError(f"No aggregate.json in {run_dir}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _summary_row(summary) -> Dict[str, Any]:
    metrics = getattr(summary, "metrics", {}) or {}
    dbg = metrics.get("debug") if isinstance(metrics.get("debug"), dict) else {}
    ver = metrics.get("verification") if isinstance(metrics.get("verification"), dict) else {}

    def _num(d: dict, key: str) -> float:
        v = d.get(key)
        try:
            return float(v) if v is not None else 0.0
        except (TypeError, ValueError):
            return 0.0

    dbg_tok = int(dbg.get("total_tokens") or 0)
    ver_tok = int(ver.get("total_tokens") or 0)
    return {
        "status": summary.status,
        "verified": summary.verified,
        "ground_truth_passed": summary.ground_truth_passed,
        "debug_self_report": getattr(summary, "debug_self_report", None),
        "debug_tokens": dbg_tok,
        "verification_tokens": ver_tok,
        "total_tokens": dbg_tok + ver_tok,
        "debug_cost": round(_num(dbg, "cost"), 4),
        "verification_cost": round(_num(ver, "cost"), 4),
        "total_cost": round(_num(dbg, "cost") + _num(ver, "cost"), 4),
        "duration_s": round(float(summary.duration_s or 0), 2),
    }


def _fmt_tri(v: Optional[bool]) -> str:
    if v is True:
        return "Y"
    if v is False:
        return "N"
    return "-"


def _load_json_if_exists(path: Path) -> Optional[Dict[str, Any]]:
    if not path.is_file():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _harness_provenance_line(run_dir: Path) -> str:
    """Compact harness fingerprint from provenance.json when present (ARCH-006)."""
    prov = _load_json_if_exists(run_dir / "provenance.json")
    if not prov:
        return "(no provenance.json)"
    parts: List[str] = []
    ru = prov.get("run_uuid")
    if ru:
        short = ru if len(ru) <= 12 else f"{ru[:8]}…"
        parts.append(f"run_uuid={short}")
    gc = prov.get("git_commit")
    if isinstance(gc, str) and gc:
        parts.append(f"git={gc[:7]}")
    rag = prov.get("rag_api") if isinstance(prov.get("rag_api"), dict) else {}
    ver = rag.get("api_version")
    if ver:
        parts.append(f"rag_api_version={ver}")
    return ", ".join(parts) if parts else "(empty provenance.json)"


def _index_summaries(run_dir: Path) -> Dict[str, Dict[str, Any]]:
    from debug_assistant_latest.report import collect_summaries_from_run

    out: Dict[str, Dict[str, Any]] = {}
    for s in collect_summaries_from_run(run_dir):
        out[s.test_name] = _summary_row(s)
    return out


def compare_runs_markdown(run_dir_a: Path, run_dir_b: Path) -> str:
    """Build a markdown report comparing two run directories."""
    agg_a = load_aggregate(run_dir_a)
    agg_b = load_aggregate(run_dir_b)
    idx_a = _index_summaries(run_dir_a)
    idx_b = _index_summaries(run_dir_b)
    tests = sorted(set(idx_a) | set(idx_b))

    id_a = agg_a.get("run_id", run_dir_a.name)
    id_b = agg_b.get("run_id", run_dir_b.name)

    lines: List[str] = [
        "## KubeLLM run comparison",
        "",
        f"| | **{id_a}** | **{id_b}** |",
        "|:---|:---|:---|",
        f"| Pass rate | {agg_a.get('pass_rate', 0)}% | {agg_b.get('pass_rate', 0)}% |",
        f"| Ground truth rate | {agg_a.get('ground_truth_rate', 0)}% | {agg_b.get('ground_truth_rate', 0)}% |",
        f"| Verified (LLM) | {agg_a.get('verified', 0)}/{agg_a.get('tests_with_verification', 0)} | {agg_b.get('verified', 0)}/{agg_b.get('tests_with_verification', 0)} |",
        f"| Total cost (USD) | {agg_a.get('total_cost', 0)} | {agg_b.get('total_cost', 0)} |",
        f"| Total tokens | {agg_a.get('total_tokens', 0)} | {agg_b.get('total_tokens', 0)} |",
        f"| Wall clock (s) | {agg_a.get('wall_clock_s', 0)} | {agg_b.get('wall_clock_s', 0)} |",
        "",
        "### Per-test",
        "",
        "| test | status A | dbg A | ver A | GT A | tok A | $ A | s A | status B | dbg B | ver B | GT B | tok B | $ B | s B |",
        "|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|",
    ]

    for name in tests:
        ra = idx_a.get(name)
        rb = idx_b.get(name)
        if ra is None:
            lines.append(
                f"| {name} | — | — | — | — | — | — | — | {rb['status']} | {_fmt_tri(rb['debug_self_report'])} | {_fmt_tri(rb['verified'])} | {_fmt_tri(rb['ground_truth_passed'])} | {rb['total_tokens']} | {rb['total_cost']} | {rb['duration_s']} |"
            )
            continue
        if rb is None:
            lines.append(
                f"| {name} | {ra['status']} | {_fmt_tri(ra['debug_self_report'])} | {_fmt_tri(ra['verified'])} | {_fmt_tri(ra['ground_truth_passed'])} | {ra['total_tokens']} | {ra['total_cost']} | {ra['duration_s']} | — | — | — | — | — | — | — |"
            )
            continue
        lines.append(
            f"| {name} | {ra['status']} | {_fmt_tri(ra['debug_self_report'])} | {_fmt_tri(ra['verified'])} | {_fmt_tri(ra['ground_truth_passed'])} | {ra['total_tokens']} | {ra['total_cost']} | {ra['duration_s']} | "
            f"{rb['status']} | {_fmt_tri(rb['debug_self_report'])} | {_fmt_tri(rb['verified'])} | {_fmt_tri(rb['ground_truth_passed'])} | {rb['total_tokens']} | {rb['total_cost']} | {rb['duration_s']} |"
        )

    lines.extend(
        [
            "",
            "### Harness / provenance",
            "",
            f"| | **{id_a}** | **{id_b}** |",
            "|:---|:---|:---|",
            f"| Snapshot | {_harness_provenance_line(run_dir_a)} | {_harness_provenance_line(run_dir_b)} |",
            "",
        ]
    )
    return "\n".join(lines)


def cmd_compare(args) -> int:
    """CLI handler for ``--compare RUN1 RUN2``."""
    pair = getattr(args, "compare", None)
    if not pair or len(pair) != 2:
        print("Error: --compare requires two run directories or run IDs.")
        return 1
    try:
        d1 = resolve_run_dir(pair[0])
        d2 = resolve_run_dir(pair[1])
    except FileNotFoundError as exc:
        print(f"Error: {exc}")
        return 1
    try:
        print(compare_runs_markdown(d1, d2))
    except FileNotFoundError as exc:
        print(f"Error: {exc}")
        return 1
    return 0
