# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Build versioned evaluation assets from prepared FAPO cases."""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Protocol, Sequence

from src.hephaestus.datasets.intent_assets import IntentCluster, IntentMatch

REQUIRED_CASE_KEYS = {"case_id", "task_type", "context", "expected", "metadata"}
SCOREABLE_EXPECTED_KEYS = {
    "answer",
    "deterministic_checks",
    "expected_output",
    "label",
    "reference_output",
    "rubric",
    "tool_expectations",
}


class EmbeddingProvider(Protocol):
    """Optional tenant adapter for production embedding backends."""

    def embed_texts(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
        """Return one dense embedding vector per input text."""


class ClusterSummarizer(Protocol):
    """Optional tenant adapter for LLM or human-readable cluster summaries."""

    def summarize_cluster(
        self,
        cluster: IntentCluster,
        representative_texts: Sequence[str],
    ) -> Mapping[str, Any]:
        """Return labels, slots, variants, and open questions for a cluster."""


class RubricExtractor(Protocol):
    """Optional tenant adapter for converting feedback into rubrics."""

    def extract_rubric(self, feedback_record: Mapping[str, Any]) -> Mapping[str, Any]:
        """Return a scorer-ready rubric or oracle payload for one feedback record."""


class SyntheticCaseGenerator(Protocol):
    """Optional tenant adapter for generating synthetic coverage cases."""

    def generate_cases(
        self,
        cluster: IntentCluster,
        trusted_oracles: Sequence[Mapping[str, Any]],
    ) -> Sequence[Mapping[str, Any]]:
        """Return synthetic FAPO case dictionaries for a matched intent cluster."""


@dataclass(frozen=True)
class FeedbackRecord:
    """Normalized feedback-bearing trace used before FAPO JSONL conversion."""

    record_id: str
    task_type: str
    user_input: str
    assistant_output: str
    polarity: str
    rationale: Optional[str] = None
    corrected_output: Optional[str] = None
    accepted_artifact: Optional[str] = None
    group_id: Optional[str] = None
    request_id: Optional[str] = None
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    tool_results: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RubricOracle:
    """Scoreable expected payload derived from feedback or review."""

    label_source: str
    confidence: float
    must: List[str] = field(default_factory=list)
    must_not: List[str] = field(default_factory=list)
    should: List[str] = field(default_factory=list)
    deterministic_checks: List[Dict[str, Any]] = field(default_factory=list)
    tool_expectations: Dict[str, Any] = field(default_factory=dict)
    reference_output: Optional[str] = None

    def to_expected(self) -> Dict[str, Any]:
        """Serialize this oracle into a FAPO case ``expected`` payload."""
        return {
            "label_source": self.label_source,
            "confidence": self.confidence,
            "rubric": {
                "must": list(self.must),
                "must_not": list(self.must_not),
                "should": list(self.should),
            },
            "deterministic_checks": list(self.deterministic_checks),
            "tool_expectations": dict(self.tool_expectations),
            "reference_output": self.reference_output,
        }


@dataclass(frozen=True)
class SyntheticFilterIssue:
    """Reason a synthetic candidate was rejected or flagged."""

    case_id: str
    code: str
    message: str


@dataclass(frozen=True)
class SyntheticFilterResult:
    """Accepted and rejected synthetic candidate cases."""

    accepted: List[Dict[str, Any]]
    rejected: List[Dict[str, Any]]
    issues: List[SyntheticFilterIssue]


@dataclass(frozen=True)
class DatasetManifest:
    """Version, source, and split metadata for an asset bundle."""

    dataset_version: str
    split_files: Dict[str, str]
    split_counts: Dict[str, int]
    source_hashes: Dict[str, str]
    settings: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the manifest for JSON output."""
        return {
            "dataset_version": self.dataset_version,
            "split_files": dict(self.split_files),
            "split_counts": dict(self.split_counts),
            "source_hashes": dict(self.source_hashes),
            "settings": dict(self.settings),
        }


def load_jsonl_dicts(path: Path) -> List[Dict[str, Any]]:
    """Load dictionaries from a JSONL file."""
    rows: List[Dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        text = line.strip()
        if not text:
            continue
        raw = json.loads(text)
        if not isinstance(raw, dict):
            raise ValueError(f"Expected JSON object at {path}:{line_number}")
        rows.append(raw)
    return rows


def load_fapo_cases(path: Path) -> List[Dict[str, Any]]:
    """Load and validate raw FAPO case dictionaries from JSONL."""
    cases = load_jsonl_dicts(path)
    for index, case in enumerate(cases, start=1):
        validate_fapo_case(case, source=f"{path}:{index}")
    return cases


def validate_fapo_case(case: Mapping[str, Any], source: str = "case") -> None:
    """Validate the generic FAPO JSONL case shape."""
    missing = REQUIRED_CASE_KEYS - set(case)
    if missing:
        raise ValueError(f"Invalid {source}: missing keys {sorted(missing)}")
    if not isinstance(case.get("case_id"), str) or not str(case.get("case_id")).strip():
        raise ValueError(f"Invalid {source}: case_id must be a non-empty string")
    if not isinstance(case.get("context"), dict):
        raise ValueError(f"Invalid {source}: context must be an object")
    if not isinstance(case.get("expected"), dict):
        raise ValueError(f"Invalid {source}: expected must be an object")
    if not isinstance(case.get("metadata"), dict):
        raise ValueError(f"Invalid {source}: metadata must be an object")


def split_cases_by_group(
    cases: Sequence[Dict[str, Any]],
    group_path: str = "metadata.group_id",
    train_fraction: float = 0.6,
    validation_fraction: float = 0.2,
    test_fraction: float = 0.2,
    seed: int = 42,
) -> Dict[str, List[Dict[str, Any]]]:
    """Split cases into train/validation/test without splitting groups."""
    _validate_fractions(train_fraction, validation_fraction, test_fraction)
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for case in cases:
        group = _stringify(_get_path(case, group_path)) or str(case["case_id"])
        groups.setdefault(group, []).append(dict(case))

    rng = random.Random(seed)
    group_items = list(groups.items())
    rng.shuffle(group_items)

    total_cases = len(cases)
    targets = {
        "train": total_cases * train_fraction,
        "validation": total_cases * validation_fraction,
        "test": total_cases * test_fraction,
    }
    split_counts = {"train": 0, "validation": 0, "test": 0}
    splits: Dict[str, List[Dict[str, Any]]] = {"train": [], "validation": [], "test": []}

    for _, group_cases in group_items:
        split_name = max(
            ("train", "validation", "test"),
            key=lambda name: (targets[name] - split_counts[name], name),
        )
        splits[split_name].extend(group_cases)
        split_counts[split_name] += len(group_cases)

    for split_cases in splits.values():
        split_cases.sort(key=lambda item: str(item["case_id"]))
    return splits


def filter_synthetic_cases(
    candidates: Sequence[Dict[str, Any]],
    existing_cases: Optional[Sequence[Dict[str, Any]]] = None,
    duplicate_threshold: float = 0.95,
) -> SyntheticFilterResult:
    """Filter synthetic candidates for validity, diversity, leakage, and solvability."""
    accepted: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []
    issues: List[SyntheticFilterIssue] = []
    fingerprints: List[set[str]] = [
        _case_fingerprint(case) for case in (existing_cases or []) if isinstance(case, dict)
    ]

    for index, candidate in enumerate(candidates, start=1):
        case_id = str(candidate.get("case_id") or f"candidate-{index}")
        candidate_issues = _synthetic_case_issues(candidate, case_id, fingerprints, duplicate_threshold)
        if candidate_issues:
            rejected.append(dict(candidate))
            issues.extend(candidate_issues)
            continue
        accepted.append(dict(candidate))
        fingerprints.append(_case_fingerprint(candidate))

    return SyntheticFilterResult(accepted=accepted, rejected=rejected, issues=issues)


def assemble_dataset_bundle(
    output_dir: Path,
    dataset_version: str,
    trusted_cases: Sequence[Dict[str, Any]],
    synthetic_cases: Sequence[Dict[str, Any]],
    regression_cases: Optional[Sequence[Dict[str, Any]]] = None,
    triage_cases: Optional[Sequence[Dict[str, Any]]] = None,
    group_path: str = "metadata.group_id",
    train_fraction: float = 0.6,
    validation_fraction: float = 0.2,
    test_fraction: float = 0.2,
    seed: int = 42,
    source_hashes: Optional[Mapping[str, str]] = None,
) -> DatasetManifest:
    """Write versioned train, validation, test, regression, and manifest files."""
    output_dir.mkdir(parents=True, exist_ok=True)

    trusted_splits = split_cases_by_group(
        trusted_cases,
        group_path=group_path,
        train_fraction=train_fraction,
        validation_fraction=validation_fraction,
        test_fraction=test_fraction,
        seed=seed,
    )
    synthetic_splits = split_cases_by_group(
        synthetic_cases,
        group_path=group_path,
        train_fraction=train_fraction,
        validation_fraction=validation_fraction,
        test_fraction=test_fraction,
        seed=seed,
    )

    split_payloads = {
        "train_feedback": trusted_splits["train"],
        "train_synthetic": synthetic_splits["train"],
        "train": trusted_splits["train"] + synthetic_splits["train"],
        "validation_trusted": trusted_splits["validation"],
        "validation_synthetic": synthetic_splits["validation"],
        "validation": trusted_splits["validation"] + synthetic_splits["validation"],
        "test_trusted": trusted_splits["test"],
        "test_synthetic": synthetic_splits["test"],
        "test": trusted_splits["test"] + synthetic_splits["test"],
        "regression_trusted": list(regression_cases or []),
        "triage_hold": list(triage_cases or []),
    }

    split_files: Dict[str, str] = {}
    split_counts: Dict[str, int] = {}
    for split_name, cases in split_payloads.items():
        path = output_dir / f"{split_name}.jsonl"
        write_jsonl(path, cases)
        split_files[split_name] = str(path)
        split_counts[split_name] = len(cases)

    manifest = DatasetManifest(
        dataset_version=dataset_version,
        split_files=split_files,
        split_counts=split_counts,
        source_hashes=dict(source_hashes or {}),
        settings={
            "group_path": group_path,
            "seed": seed,
            "train_fraction": train_fraction,
            "validation_fraction": validation_fraction,
            "test_fraction": test_fraction,
        },
    )
    manifest_path = output_dir / "dataset_manifest.json"
    manifest_path.write_text(json.dumps(manifest.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
    return manifest


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    """Write mappings as JSONL with deterministic object key order."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(dict(row), sort_keys=True) + "\n")


def write_coverage_report(
    path: Path,
    clusters: Sequence[IntentCluster],
    matches: Sequence[IntentMatch],
) -> None:
    """Write a Markdown coverage report from intent clusters and matches."""
    match_by_cluster = {match.cluster_id: match for match in matches}
    matched = [match for match in matches if match.status == "matched_trusted_intent"]
    needs_more = [match for match in matches if match.status == "needs_more_trusted_examples"]
    missing = [match for match in matches if match.status == "missing_or_weak_labels"]

    lines = [
        "<!--",
        "Copyright 2026 Cisco Systems, Inc. and its affiliates",
        "",
        "SPDX-License-Identifier: Apache-2.0",
        "-->",
        "",
        "# Evaluation Asset Coverage Report",
        "",
        "## Summary",
        "",
        f"- Intent clusters: {len(clusters)}",
        f"- Matched trusted intents: {len(matched)}",
        f"- Needs more trusted examples: {len(needs_more)}",
        f"- Missing or weak labels: {len(missing)}",
        "",
        "## Clusters",
        "",
        "| Cluster | Route | Size | Status | Match | Trusted Examples | Reason | Top Terms |",
        "|---|---|---:|---|---|---:|---|---|",
    ]
    for cluster in sorted(clusters, key=lambda item: (-item.size, item.cluster_id)):
        match = match_by_cluster.get(cluster.cluster_id)
        status = match.status if match else "unmatched"
        label = match.matched_label if match and match.matched_label else ""
        trusted_count = match.trusted_example_count if match else 0
        reason = match.reason if match else ""
        lines.append(
            "| "
            f"`{cluster.cluster_id}` | `{cluster.route}` | {cluster.size} | "
            f"{status} | {label} | {trusted_count} | {reason} | {', '.join(cluster.top_terms)} |"
        )

    lines.extend(["", "## Feedback Requests", ""])
    feedback_requests = needs_more + missing
    if feedback_requests:
        for match in feedback_requests:
            lines.append(
                f"- `{match.cluster_id}` requires more trusted evidence "
                f"({match.status}: {match.reason}); route representative examples to "
                "application feedback prompts, annotation, or SME review."
            )
    else:
        lines.append("- No trusted-evidence gaps found.")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def synthetic_issue_to_dict(issue: SyntheticFilterIssue) -> Dict[str, Any]:
    """Serialize a synthetic filtering issue for JSONL output."""
    return {
        "case_id": issue.case_id,
        "code": issue.code,
        "message": issue.message,
    }


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest for a file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _synthetic_case_issues(
    case: Mapping[str, Any],
    case_id: str,
    existing_fingerprints: Sequence[set[str]],
    duplicate_threshold: float,
) -> List[SyntheticFilterIssue]:
    issues: List[SyntheticFilterIssue] = []
    try:
        validate_fapo_case(case, source=case_id)
    except ValueError as exc:
        issues.append(SyntheticFilterIssue(case_id=case_id, code="invalid_schema", message=str(exc)))
        return issues

    context = case["context"]
    expected = case["expected"]
    if not context:
        issues.append(
            SyntheticFilterIssue(
                case_id=case_id,
                code="unsolvable",
                message="context is empty",
            )
        )
    if not _has_scoreable_expected(expected):
        issues.append(
            SyntheticFilterIssue(
                case_id=case_id,
                code="not_scoreable",
                message="expected lacks rubric, checks, reference, answer, label, or tool expectations",
            )
        )
    if _has_label_leakage(context, expected):
        issues.append(
            SyntheticFilterIssue(
                case_id=case_id,
                code="label_leakage",
                message="expected labels or rationale appear in runtime context",
            )
        )

    fingerprint = _case_fingerprint(case)
    for existing in existing_fingerprints:
        if _jaccard(fingerprint, existing) >= duplicate_threshold:
            issues.append(
                SyntheticFilterIssue(
                    case_id=case_id,
                    code="near_duplicate",
                    message="case is too similar to an existing accepted case",
                )
            )
            break
    return issues


def _has_scoreable_expected(expected: Mapping[str, Any]) -> bool:
    if not SCOREABLE_EXPECTED_KEYS.intersection(expected):
        return False
    rubric = expected.get("rubric")
    if isinstance(rubric, Mapping):
        criteria = []
        for key in ("must", "must_not", "should"):
            value = rubric.get(key, [])
            if isinstance(value, list):
                criteria.extend(item for item in value if str(item).strip())
        if criteria:
            return True
    for key in ("deterministic_checks",):
        value = expected.get(key)
        if isinstance(value, list) and value:
            return True
    for key in ("answer", "expected_output", "label", "reference_output"):
        if _stringify(expected.get(key)):
            return True
    tool_expectations = expected.get("tool_expectations")
    return isinstance(tool_expectations, Mapping) and bool(tool_expectations)


def _case_fingerprint(case: Mapping[str, Any]) -> set[str]:
    return set(_tokenize_for_filter(_stringify(case.get("context", {}))))


def _has_label_leakage(context: Mapping[str, Any], expected: Mapping[str, Any]) -> bool:
    context_text = _stringify(context).lower()
    for key in ("feedback_rationale", "rationale", "corrected_output", "reference_output"):
        value = _get_path(expected, key)
        if isinstance(value, str):
            candidate = " ".join(value.lower().split())
            if len(candidate) >= 24 and candidate in context_text:
                return True
    return False


def _tokenize_for_filter(text: str) -> List[str]:
    return [token for token in text.lower().replace("_", " ").split() if len(token) > 1]


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def _validate_fractions(train_fraction: float, validation_fraction: float, test_fraction: float) -> None:
    fractions = (train_fraction, validation_fraction, test_fraction)
    if any(value < 0 for value in fractions):
        raise ValueError("split fractions must be non-negative")
    if not 0.999 <= sum(fractions) <= 1.001:
        raise ValueError("train, validation, and test fractions must sum to 1.0")


def _get_path(raw: Any, path: str) -> Any:
    value = raw
    for part in path.split("."):
        if isinstance(value, Mapping):
            value = value.get(part)
        elif isinstance(value, list) and part.isdigit():
            index = int(part)
            value = value[index] if index < len(value) else None
        else:
            return None
    return value


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return " ".join(value.split())
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, list):
        return " ".join(_stringify(item) for item in value)
    if isinstance(value, Mapping):
        return json.dumps(value, sort_keys=True)
    return str(value)
