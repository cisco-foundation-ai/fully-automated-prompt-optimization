# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Post-hoc failure attribution from eval results.

Loads a results.jsonl file, identifies failed cases, and attributes
failures to specific chain steps using rule-based heuristics.

Supports format failure detection, cascading failure tracking,
retrieval quality tiers, confidence scoring, and per-level summaries.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


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


def attribute_failures(
    results_path: Path,
    threshold: float = 100.0,
) -> Dict[str, Dict[str, Any]]:
    """Attribute failures to chain steps.

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

    attribution: Dict[str, Dict[str, Any]] = {}

    failed = [r for r in results if float(r.get("composite_score", 0)) < threshold]
    if not failed:
        return attribution

    for case in failed:
        case_id = case.get("case_id", "unknown")
        step_outputs: Dict[str, str] = case.get("step_outputs", {})
        context: Dict[str, str] = case.get("context", {})
        expected_answer = case.get("expected_answer", context.get("answer", ""))
        tool_history: List[Dict[str, Any]] = case.get("tool_call_history", [])

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
            - total_failures: total failure count
            - by_confidence: {high: N, medium: N, low: N}
            - by_retrieval_tier: {hit: N, partial: N, miss: N}
            - tool_error_types: {timeout: N, not_found: N, invalid_args: N, ...}
    """
    prompt_count = 0
    structural_count = 0
    tool_count = 0
    format_count = 0
    total_count = 0
    by_confidence: Dict[str, int] = {"high": 0, "medium": 0, "low": 0}
    by_retrieval_tier: Dict[str, int] = {"hit": 0, "partial": 0, "miss": 0}
    tool_error_types: Dict[str, int] = {}

    for info in attribution.values():
        count = info["count"]
        total_count += count
        heuristic = info.get("heuristic", "")
        confidence = info.get("confidence", "low")
        by_confidence[confidence] = by_confidence.get(confidence, 0) + count

        if info.get("retrieval_tier"):
            tier = info["retrieval_tier"]
            by_retrieval_tier[tier] = by_retrieval_tier.get(tier, 0) + count

        # Track tool error types
        if info.get("tool_failure"):
            error_type = info.get("tool_error_type", "other")
            tool_error_types[error_type] = tool_error_types.get(error_type, 0) + count

        # Classify by optimization level
        if heuristic.startswith("tool_failure_"):
            tool_count += count
        elif heuristic in ("retrieval_empty", "retrieval_overlap", "cascade"):
            structural_count += count
        elif heuristic == "cascade_downstream":
            pass  # Already counted via cascade root
            total_count -= count  # Don't double-count
        elif heuristic == "format_failure":
            prompt_count += count
            format_count += count
        elif heuristic in ("final_step_fallback", "empty_intermediate"):
            prompt_count += count
        else:
            prompt_count += count

    return {
        "prompt_addressable": prompt_count,
        # Skills are a co-equal textual level: the same reasoning/format failures
        # that prompt edits address can also be addressed by skill edits.
        "skill_addressable": prompt_count,
        "structural_addressable": structural_count,
        "tool_addressable": tool_count,
        "format_failures": format_count,
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
        }
        if retrieval_tier:
            attribution[step_name]["retrieval_tier"] = retrieval_tier
        if cascade_root:
            attribution[step_name]["cascade_root"] = cascade_root
        if format_failure:
            attribution[step_name]["format_failures"] = 0
        if tool_failure:
            attribution[step_name]["tool_failure"] = True
            attribution[step_name]["tool_error_type"] = tool_error_type
    attribution[step_name]["count"] += 1
    attribution[step_name]["case_ids"].append(case_id)
    if format_failure:
        attribution[step_name]["format_failures"] = (
            attribution[step_name].get("format_failures", 0) + 1
        )
