# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Post-hoc failure attribution from evaluation results.

Analyzes result rows in memory, optionally joining verified case evidence, and
attributes failures to specific chain steps using rule-based heuristics. A legacy
file-only wrapper deliberately remains context-free.

Supports format failure detection, cascading failure tracking,
retrieval quality tiers, confidence scoring, and per-level summaries.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any, Dict, List, Optional

INFRASTRUCTURE_FAILURE_KEY = "__infrastructure__"


def _is_retrieval_step(step_name: str) -> bool:
    """Heuristic: step names containing 'retriev' or 'search' are retrieval."""
    lower = step_name.lower()
    return "retriev" in lower or "search" in lower or "fetch" in lower


def _retrieval_overlap(step_output: str, context: Dict[str, str]) -> float:
    """Return token overlap ratio between query and retrieval output."""
    if not step_output or not step_output.strip():
        return 0.0
    query = context.get("question", context.get("query", ""))
    if not query:
        return 1.0  # No query to compare — assume acceptable
    query_tokens = set(query.lower().split())
    if not query_tokens:
        return 1.0
    output_tokens = set(step_output.lower().split())
    return len(query_tokens & output_tokens) / len(query_tokens)


def _retrieval_tier(overlap: float) -> str:
    """Classify retrieval quality into tiers."""
    if overlap >= 0.4:
        return "hit"
    elif overlap >= 0.2:
        return "partial"
    else:
        return "miss"


def _detect_format_failure(
    final_output: str, expected_answer: Optional[str]
) -> bool:
    """Detect if the final output contains the answer but in wrong format.

    Checks if the expected answer appears within the output but the output
    contains extra surrounding text (explanations, caveats, etc.).
    """
    if not final_output or not expected_answer:
        return False
    final_stripped = final_output.strip()
    answer_stripped = expected_answer.strip()
    if not answer_stripped:
        return False
    # Exact match means no format issue
    if final_stripped == answer_stripped:
        return False
    # Answer is contained but output has extra text — format failure
    if answer_stripped.lower() in final_stripped.lower():
        # Only flag if output is significantly longer than the answer
        if len(final_stripped) > len(answer_stripped) * 1.5:
            return True
    return False


def _detect_cascading_failures(
    step_outputs: Dict[str, str],
) -> Optional[str]:
    """Detect if an early empty/degraded step caused downstream failures.

    Returns the cascade root step name, or None if no cascade detected.
    """
    step_names = list(step_outputs.keys())
    if len(step_names) < 2:
        return None

    for i, step_name in enumerate(step_names[:-1]):
        output = str(step_outputs[step_name])
        if not output or not output.strip():
            # Check if downstream steps also failed
            downstream_empty = 0
            for downstream in step_names[i + 1 :]:
                downstream_out = str(step_outputs[downstream])
                if not downstream_out or not downstream_out.strip():
                    downstream_empty += 1
            # If at least one downstream step also failed, this is a cascade
            if downstream_empty > 0:
                return step_name
    return None


def _detect_tool_failures(tool_history: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Detect if tool execution failures caused the chain to fail.

    Args:
        tool_history: List of tool call records with tool, arguments, error, etc.

    Returns:
        Dict with failed tool info, or None if no tool failures
    """
    if not tool_history:
        return None

    failed_tools = [tc for tc in tool_history if tc.get("error")]
    if not failed_tools:
        return None

    # Return info about the first failed tool
    first_failure = failed_tools[0]
    return {
        "tool": first_failure.get("tool", "unknown"),
        "error": first_failure.get("error", ""),
        "iteration": first_failure.get("iteration", 0),
        "total_failures": len(failed_tools),
    }


def _classify_tool_error(error_message: str) -> str:
    """Classify tool error by type.

    Args:
        error_message: Error message from tool execution

    Returns:
        Error category: "timeout", "not_found", "invalid_args", "permission", "other"
    """
    error_lower = error_message.lower()

    if "timeout" in error_lower or "timed out" in error_lower:
        return "timeout"
    elif "not found" in error_lower or "unknown tool" in error_lower:
        return "not_found"
    elif "invalid" in error_lower or "missing" in error_lower or "required" in error_lower:
        return "invalid_args"
    elif "permission" in error_lower or "forbidden" in error_lower or "unauthorized" in error_lower:
        return "permission"
    else:
        return "other"


def _confidence_for_heuristic(
    heuristic: str, overlap: Optional[float] = None
) -> str:
    """Assign confidence level based on how decisive the heuristic was."""
    if heuristic == "retrieval_empty":
        return "high"
    elif heuristic == "retrieval_overlap":
        if overlap is not None and (overlap < 0.1 or overlap > 0.35):
            return "high"  # Clear miss or clear partial
        return "medium"  # Borderline
    elif heuristic == "empty_intermediate":
        return "high"
    elif heuristic == "cascade":
        return "high"
    elif heuristic == "format_failure":
        return "medium"
    elif heuristic == "final_step_fallback":
        return "low"
    else:
        return "low"


def _record_value(record: Any, name: str, default: Any = None) -> Any:
    """Read one field from either a serialized row or a result/case object."""
    if isinstance(record, Mapping):
        return record.get(name, default)
    return getattr(record, name, default)


def _record_case_id(record: Any) -> str:
    """Return a valid case ID without exposing any other record content."""
    case_id = _record_value(record, "case_id")
    if not isinstance(case_id, str) or not case_id:
        raise ValueError("Attribution inputs require a non-empty string case_id")
    return case_id


def _join_cases_by_order(
    results: List[Any], cases: Optional[Iterable[Any]]
) -> Dict[str, Any]:
    """Validate and build an exact ordered in-memory case join."""
    if cases is None:
        return {}

    case_list = list(cases)
    result_ids = [_record_case_id(result) for result in results]
    case_ids = [_record_case_id(case) for case in case_list]
    if result_ids != case_ids:
        raise ValueError(
            "Cannot join attribution inputs: ordered case IDs do not match"
        )
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("Cannot join attribution inputs with duplicate case IDs")
    return dict(zip(case_ids, case_list))


def _joined_case_evidence(case: Any) -> tuple[Dict[str, str], Optional[str]]:
    """Extract transient diagnostic evidence from one verified in-memory case."""
    if case is None:
        return {}, None

    raw_context = _record_value(case, "context", {})
    context = (
        {str(key): str(value) for key, value in raw_context.items()}
        if isinstance(raw_context, Mapping)
        else {}
    )

    expected = _record_value(case, "expected", {})
    if not isinstance(expected, Mapping):
        return context, str(expected) if expected is not None else None

    for key in (
        "answer",
        "expected_answer",
        "reference_output",
        "label",
        "cwe_id",
    ):
        value = expected.get(key)
        if isinstance(value, (str, int, float, bool)):
            return context, str(value)
    return context, None


def _is_execution_failure(result: Any) -> bool:
    """Return whether a result explicitly represents an infrastructure failure."""
    status = _record_value(result, "execution_status")
    if status is None:
        return bool(_record_value(result, "execution_error"))
    return str(status).strip().lower() not in {
        "success",
        "succeeded",
        "completed",
    }


def _infrastructure_failure_stage(result: Any) -> str:
    """Classify an execution failure into a small, non-sensitive allowlist."""
    provenance = _record_value(result, "evaluation_provenance", {})
    if isinstance(provenance, Mapping):
        for key in ("failure_stage", "component"):
            candidate = str(provenance.get(key, "")).strip().lower()
            if candidate in {"provider", "chain", "scorer", "mcp"}:
                return candidate

    raw_error = _record_value(result, "execution_error", {})
    if isinstance(raw_error, Mapping):
        candidate = str(raw_error.get("phase", "")).strip().lower()
        if candidate in {"provider", "chain", "scorer", "mcp"}:
            return candidate

    error = str(raw_error).lower()
    for candidate in ("provider", "chain", "scorer", "mcp"):
        if candidate in error:
            return candidate
    return "unknown"


def attribute_failures(
    results_path: Path,
    threshold: float = 100.0,
) -> Dict[str, Dict[str, Any]]:
    """Attribute a legacy results file without loading protected case data.

    Args:
        results_path: Path to a results.jsonl file.
        threshold: Cases with composite_score < threshold are considered failed.

    Returns:
        Dict mapping step names to:
            - count: number of cases where this step was attributed as failing
            - case_ids: list of representative case IDs
            - heuristic: which detection method was used
            - confidence: high/medium/low
            - retrieval_tier: hit/partial/miss (retrieval steps only)
            - cascade_root: step name if this is a cascading failure
            - format_failures: count of format-related failures (final step only)
    """
    results: List[Dict[str, Any]] = []
    with results_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                results.append(json.loads(line))

    return attribute_results(results, threshold=threshold)


def attribute_verified_run(
    output_dir: Path,
    threshold: float = 100.0,
) -> Dict[str, Dict[str, Any]]:
    """Attribute one authoritative run using its exact recorded dataset.

    The run bundle, complete run identity, dataset bytes, and ordered case IDs
    must all validate before protected case evidence is joined in memory. Any
    mismatch fails closed; this function never falls back to loose result files.

    Args:
        output_dir: Directory containing an authoritative terminal run bundle.
        threshold: Successful cases below this score are considered failed.

    Returns:
        The same aggregate mapping as :func:`attribute_results`.
    """
    from src.hephaestus.datasets.jsonl_loader import load_cases_with_identity
    from src.hephaestus.runs.bundle import load_run_bundle
    from src.hephaestus.runs.identity import validate_run_identity_payload

    bundle = load_run_bundle(Path(output_dir))
    identity = validate_run_identity_payload(bundle.run_identity)
    controls = identity.always_controls

    dataset_path = controls["dataset_path"]
    if bundle.run_config.get("dataset_path") != dataset_path:
        raise ValueError("run bundle dataset path does not match run identity")

    dataset_control = controls["dataset"]
    if dataset_control.get("status") != "available":
        raise ValueError("run identity dataset fingerprint is unavailable")

    loaded = load_cases_with_identity(Path(dataset_path))
    actual_fingerprint = f"sha256:{loaded.raw_sha256}"
    if actual_fingerprint != dataset_control["fingerprint"]:
        raise ValueError("dataset fingerprint does not match run identity")

    expected_case_ids = tuple(controls["ordered_case_ids"])
    if loaded.ordered_case_ids != expected_case_ids:
        raise ValueError("dataset ordered case IDs do not match run identity")

    cases_by_id = {case.case_id: case for case in loaded.cases}
    joined_cases = [cases_by_id[_record_case_id(result)] for result in bundle.results]
    return attribute_results(bundle.results, joined_cases, threshold=threshold)


def attribute_results(
    results: Iterable[Any],
    cases: Optional[Iterable[Any]] = None,
    threshold: float = 100.0,
) -> Dict[str, Dict[str, Any]]:
    """Attribute failures using an optional verified, in-memory case join.

    ``cases`` must have exactly the same ordered IDs as ``results``. Protected
    context and expected values are used transiently and never returned. File-only
    callers omit ``cases`` and therefore remain context-free.

    Args:
        results: Serialized result rows or result objects.
        cases: Corresponding case rows or objects already verified by the caller.
        threshold: Successful cases below this score are considered failed.

    Returns:
        Per-step aggregate attribution. Explicit execution failures are reported
        separately under ``__infrastructure__``.
    """
    result_list = list(results)
    cases_by_id = _join_cases_by_order(result_list, cases)
    attribution: Dict[str, Dict[str, Any]] = {}

    for result in result_list:
        case_id = _record_case_id(result)
        if _is_execution_failure(result):
            _add_attribution(
                attribution,
                INFRASTRUCTURE_FAILURE_KEY,
                case_id,
                heuristic="execution_failure",
                confidence="high",
            )
            infrastructure = attribution[INFRASTRUCTURE_FAILURE_KEY]
            infrastructure["infrastructure_failure"] = True
            stage = _infrastructure_failure_stage(result)
            if "failure_stage" not in infrastructure:
                infrastructure["failure_stage"] = stage
            stage_counts = infrastructure.setdefault("failure_stage_counts", {})
            stage_counts[stage] = stage_counts.get(stage, 0) + 1
            continue

        if float(_record_value(result, "composite_score", 0)) >= threshold:
            continue

        raw_step_outputs = _record_value(result, "step_outputs", {})
        step_outputs: Dict[str, str] = (
            dict(raw_step_outputs) if isinstance(raw_step_outputs, Mapping) else {}
        )
        context, expected_answer = _joined_case_evidence(cases_by_id.get(case_id))
        raw_tool_history = _record_value(result, "tool_call_history", [])
        tool_history: List[Dict[str, Any]] = (
            list(raw_tool_history) if isinstance(raw_tool_history, list) else []
        )

        if not step_outputs:
            _add_attribution(
                attribution,
                "__no_steps__",
                case_id,
                heuristic="no_steps",
                confidence="high",
            )
            continue

        # Check for tool failures first (highest priority)
        tool_failure_info = _detect_tool_failures(tool_history)
        if tool_failure_info:
            error_type = _classify_tool_error(tool_failure_info["error"])
            _add_attribution(
                attribution,
                f"tool_{tool_failure_info['tool']}",
                case_id,
                heuristic=f"tool_failure_{error_type}",
                confidence="high",
                tool_failure=True,
                tool_error_type=error_type,
            )
            continue

        step_names = list(step_outputs.keys())

        # Check for cascading failures first
        cascade_root = _detect_cascading_failures(step_outputs)
        if cascade_root:
            _add_attribution(
                attribution,
                cascade_root,
                case_id,
                heuristic="cascade",
                confidence="high",
                cascade_root=cascade_root,
            )
            # Also tag downstream steps as cascading
            found_root = False
            for sn in step_names:
                if sn == cascade_root:
                    found_root = True
                    continue
                if found_root:
                    _add_attribution(
                        attribution,
                        sn,
                        case_id,
                        heuristic="cascade_downstream",
                        confidence="high",
                        cascade_root=cascade_root,
                    )
            continue

        attributed = False

        # Check retrieval steps with tiered quality
        for step_name in step_names:
            output = str(step_outputs[step_name])
            if _is_retrieval_step(step_name):
                if not output or not output.strip():
                    _add_attribution(
                        attribution,
                        step_name,
                        case_id,
                        heuristic="retrieval_empty",
                        confidence="high",
                        retrieval_tier="miss",
                    )
                    attributed = True
                    break
                overlap = _retrieval_overlap(output, context)
                tier = _retrieval_tier(overlap)
                if tier in ("miss", "partial"):
                    _add_attribution(
                        attribution,
                        step_name,
                        case_id,
                        heuristic="retrieval_overlap",
                        confidence=_confidence_for_heuristic(
                            "retrieval_overlap", overlap
                        ),
                        retrieval_tier=tier,
                    )
                    attributed = True
                    break

        if attributed:
            continue

        # Check for empty intermediate outputs (non-final steps)
        for step_name in step_names[:-1]:
            output = str(step_outputs[step_name])
            if not output or not output.strip():
                _add_attribution(
                    attribution,
                    step_name,
                    case_id,
                    heuristic="empty_intermediate",
                    confidence="high",
                )
                attributed = True
                break

        if attributed:
            continue

        # Check for format failure on final step
        if step_names:
            final_output = str(step_outputs[step_names[-1]])
            if _detect_format_failure(final_output, expected_answer):
                _add_attribution(
                    attribution,
                    step_names[-1],
                    case_id,
                    heuristic="format_failure",
                    confidence="medium",
                    format_failure=True,
                )
                continue

        # If all intermediate steps have output but case still failed,
        # attribute to the final step
        if step_names:
            _add_attribution(
                attribution,
                step_names[-1],
                case_id,
                heuristic="final_step_fallback",
                confidence="low",
            )

    return attribution


def summarize(attribution: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Summarize attribution results by optimization level.

    Returns:
        Dict with:
            - prompt_addressable: count of failures fixable by prompt changes
            - skill_addressable: count of failures fixable by skill changes. Skills
              and prompts are co-equal textual levels addressing the same class of
              reasoning/format failures, so this mirrors prompt_addressable. The
              optimization agent decides — per its task scope — whether to fix a
              textual failure via prompt edits, skill edits, or both.
            - structural_addressable: count of failures fixable by structural changes
            - tool_addressable: count of failures fixable by tool/MCP changes
            - format_failures: count of format-related failures
            - infrastructure_failures: count of failed case executions
            - total_failures: total failure count
            - by_confidence: {high: N, medium: N, low: N}
            - by_retrieval_tier: {hit: N, partial: N, miss: N}
            - tool_error_types: {timeout: N, not_found: N, invalid_args: N, ...}
    """
    prompt_count = 0
    structural_count = 0
    tool_count = 0
    format_count = 0
    infrastructure_count = 0
    total_count = 0
    by_confidence: Dict[str, int] = {"high": 0, "medium": 0, "low": 0}
    by_retrieval_tier: Dict[str, int] = {"hit": 0, "partial": 0, "miss": 0}
    tool_error_types: Dict[str, int] = {}

    for info in attribution.values():
        count = info["count"]
        total_count += count
        heuristic_counts = info.get("heuristic_counts")
        if not isinstance(heuristic_counts, Mapping):
            heuristic_counts = {info.get("heuristic", ""): count}
        confidence_counts = info.get("confidence_counts")
        if not isinstance(confidence_counts, Mapping):
            confidence_counts = {info.get("confidence", "low"): count}
        for confidence, confidence_count in confidence_counts.items():
            by_confidence[str(confidence)] = (
                by_confidence.get(str(confidence), 0) + int(confidence_count)
            )

        retrieval_tier_counts = info.get("retrieval_tier_counts")
        if not isinstance(retrieval_tier_counts, Mapping):
            tier = info.get("retrieval_tier")
            retrieval_tier_counts = {tier: count} if tier else {}
        for tier, tier_count in retrieval_tier_counts.items():
            by_retrieval_tier[str(tier)] = (
                by_retrieval_tier.get(str(tier), 0) + int(tier_count)
            )

        if info.get("infrastructure_failure"):
            infrastructure_count += count
            continue

        # Track tool error types
        if info.get("tool_failure"):
            error_counts = info.get("tool_error_type_counts")
            if not isinstance(error_counts, Mapping):
                error_type = info.get("tool_error_type", "other")
                error_counts = {error_type: count}
            for error_type, error_count in error_counts.items():
                tool_error_types[str(error_type)] = (
                    tool_error_types.get(str(error_type), 0) + int(error_count)
                )

        # Classify by optimization level
        for heuristic, observation_count in heuristic_counts.items():
            heuristic = str(heuristic)
            observation_count = int(observation_count)
            if heuristic.startswith("tool_failure_"):
                tool_count += observation_count
            elif heuristic in ("retrieval_empty", "retrieval_overlap", "cascade"):
                structural_count += observation_count
            elif heuristic == "cascade_downstream":
                total_count -= observation_count
            elif heuristic == "format_failure":
                prompt_count += observation_count
                format_count += observation_count
            else:
                prompt_count += observation_count

    return {
        "prompt_addressable": prompt_count,
        # Skills are a co-equal textual level: the same reasoning/format failures
        # that prompt edits address can also be addressed by skill edits.
        "skill_addressable": prompt_count,
        "structural_addressable": structural_count,
        "tool_addressable": tool_count,
        "format_failures": format_count,
        "infrastructure_failures": infrastructure_count,
        "total_failures": total_count,
        "by_confidence": by_confidence,
        "by_retrieval_tier": by_retrieval_tier,
        "tool_error_types": tool_error_types,
    }


def _add_attribution(
    attribution: Dict[str, Dict[str, Any]],
    step_name: str,
    case_id: str,
    heuristic: str = "",
    confidence: str = "low",
    retrieval_tier: Optional[str] = None,
    cascade_root: Optional[str] = None,
    format_failure: bool = False,
    tool_failure: bool = False,
    tool_error_type: Optional[str] = None,
) -> None:
    """Add a failure attribution entry."""
    if step_name not in attribution:
        attribution[step_name] = {
            "count": 0,
            "case_ids": [],
            "heuristic": heuristic,
            "confidence": confidence,
            "heuristic_counts": {},
            "confidence_counts": {},
        }
    entry = attribution[step_name]
    entry["count"] += 1
    entry["case_ids"].append(case_id)

    heuristic_counts = entry.setdefault("heuristic_counts", {})
    heuristic_counts[heuristic] = heuristic_counts.get(heuristic, 0) + 1
    confidence_counts = entry.setdefault("confidence_counts", {})
    confidence_counts[confidence] = confidence_counts.get(confidence, 0) + 1

    if retrieval_tier:
        entry.setdefault("retrieval_tier", retrieval_tier)
        tier_counts = entry.setdefault("retrieval_tier_counts", {})
        tier_counts[retrieval_tier] = tier_counts.get(retrieval_tier, 0) + 1
    if cascade_root:
        entry.setdefault("cascade_root", cascade_root)
        root_counts = entry.setdefault("cascade_root_counts", {})
        root_counts[cascade_root] = root_counts.get(cascade_root, 0) + 1
    if tool_failure:
        entry["tool_failure"] = True
        entry.setdefault("tool_error_type", tool_error_type)
        error_counts = entry.setdefault("tool_error_type_counts", {})
        error_counts[tool_error_type] = error_counts.get(tool_error_type, 0) + 1
    if format_failure:
        entry["format_failures"] = entry.get("format_failures", 0) + 1
