# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for the separate Evaluation Asset Studio frontend."""

from __future__ import annotations

import json
import re
import shutil
import subprocess

import pytest

from src.hephaestus.webui.evaluation_assets_frontend import EVALUATION_ASSET_HTML
from src.hephaestus.webui.frontend import INDEX_HTML


def _run_frontend_expression(expression: str, payload: object) -> str:
    """Evaluate one pure renderer from the inline frontend with Node.js."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is required to exercise the inline browser renderer")
    scripts = re.findall(r"<script>([\s\S]*?)</script>", EVALUATION_ASSET_HTML)
    assert len(scripts) == 1
    script = scripts[0]
    script = script[: script.rfind("boot().catch")]
    script += f"\nconst TEST_PAYLOAD = {json.dumps(payload)};\n"
    script += (
        f"Promise.resolve({expression}).then(value => "
        "process.stdout.write(String(value))).catch(error => { "
        "console.error(error); process.exitCode = 1; });\n"
    )
    completed = subprocess.run(
        [node, "-"],
        input=script,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return completed.stdout


def test_asset_studio_owns_creation_controls() -> None:
    assert "FAPO Evaluation Asset Studio" in EVALUATION_ASSET_HTML
    assert "<strong>Evaluation Asset Studio</strong>" in EVALUATION_ASSET_HTML
    assert "FAPO data preparation" not in EVALUATION_ASSET_HTML
    assert "/api/evaluation-assets/start" in EVALUATION_ASSET_HTML
    assert 'id="view-contract"' in EVALUATION_ASSET_HTML
    assert "Required on every record" in EVALUATION_ASSET_HTML
    assert "Complete labeled example" in EVALUATION_ASSET_HTML
    assert "Do not include <code>feedback</code>" in EVALUATION_ASSET_HTML
    assert 'value="gpt-5.5"' in EVALUATION_ASSET_HTML
    assert 'value="gpt-4o-mini"' in EVALUATION_ASSET_HTML
    assert 'value="text-embedding-3-small"' in EVALUATION_ASSET_HTML
    assert 'value="text-embedding-ada-002"' in EVALUATION_ASSET_HTML
    assert 'value="tfidf"' in EVALUATION_ASSET_HTML
    assert 'name="cluster_count"' in EVALUATION_ASSET_HTML
    assert (
        "Set this higher than the number of routes and lower than the number "
        "of unlabeled data points."
    ) in EVALUATION_ASSET_HTML
    assert 'name="match_threshold"' in EVALUATION_ASSET_HTML
    assert 'value="0.6"' in EVALUATION_ASSET_HTML
    assert 'name="synthetic_coverage_enabled"' in EVALUATION_ASSET_HTML
    assert 'name="synthetic_cases_per_cluster"' in EVALUATION_ASSET_HTML
    assert "Disabled" in EVALUATION_ASSET_HTML
    assert "raw feedback and unlabeled conversations" in EVALUATION_ASSET_HTML
    assert "Interactive clustering view" in EVALUATION_ASSET_HTML
    assert "Artifact guide" in EVALUATION_ASSET_HTML
    assert "renderArtifactMenu(artifacts)" in EVALUATION_ASSET_HTML
    assert "Non-probability acquisition queue" in EVALUATION_ASSET_HTML
    assert "Example data" in EVALUATION_ASSET_HTML
    assert "Report unsupported clusters" in EVALUATION_ASSET_HTML
    assert "Assign trusted groups to splits before guideline creation" in EVALUATION_ASSET_HTML
    assert "Publish finalized versioned tenant datasets" in EVALUATION_ASSET_HTML
    assert "Match coverage" in EVALUATION_ASSET_HTML
    assert "stageCardResult(stage, counts)" in EVALUATION_ASSET_HTML
    assert "stage.message ||" not in EVALUATION_ASSET_HTML
    assert "assetRevision(nextAssets) === assetRevision(APP.assets)" in EVALUATION_ASSET_HTML
    assert "captureViewScroll()" in EVALUATION_ASSET_HTML
    assert "restoreViewScroll(scrollPosition)" in EVALUATION_ASSET_HTML
    assert "Rendered artifact" in EVALUATION_ASSET_HTML
    assert "renderCoverageMarkdown(report.content || report.preview)" in EVALUATION_ASSET_HTML
    assert "detail.stage === 'coverage_decisions' ? renderCoverageReport(detail)" in EVALUATION_ASSET_HTML
    assert "/stages/" in EVALUATION_ASSET_HTML
    assert "Select the failed stage below to adjust its input parameters." in EVALUATION_ASSET_HTML
    assert "Adjust inputs for" in EVALUATION_ASSET_HTML
    assert "Save decisions &amp; resume" in EVALUATION_ASSET_HTML
    assert "config_history.jsonl" in EVALUATION_ASSET_HTML
    assert "Changing this rebuilds from Stage 5." in EVALUATION_ASSET_HTML
    assert 'name="min_trusted_examples"' in EVALUATION_ASSET_HTML
    assert 'name="split_seed"' in EVALUATION_ASSET_HTML
    assert "Raw inputs are immutable inside an asset." in EVALUATION_ASSET_HTML
    assert "Extend asset" in EVALUATION_ASSET_HTML
    assert (
        '<button class="primary extend-primary" id="extend">Extend asset</button>'
        in EVALUATION_ASSET_HTML
    )
    assert "Keep original clustering" in EVALUATION_ASSET_HTML
    assert "Rerun clustering" in EVALUATION_ASSET_HTML
    assert "/api/evaluation-assets/extend" in EVALUATION_ASSET_HTML
    assert "Guideline creation model" in EVALUATION_ASSET_HTML
    assert "Create guidelines" in EVALUATION_ASSET_HTML
    assert "Extract only new evidence and rebuild guidelines" in EVALUATION_ASSET_HTML
    for status in (
        "draft",
        "queued",
        "running",
        "awaiting_review",
        "released",
        "failed",
    ):
        assert f"status-{status}" in EVALUATION_ASSET_HTML
    assert "state.status === 'released'" in EVALUATION_ASSET_HTML
    assert "/adopt" in EVALUATION_ASSET_HTML
    assert "Adopt verified legacy asset" in EVALUATION_ASSET_HTML


def test_explorer_links_to_studio_without_asset_form() -> None:
    assert 'href="/evaluation-assets/"' in INDEX_HTML
    assert 'class="studio-nav"' in INDEX_HTML
    assert "Open Evaluation Asset Studio" in INDEX_HTML
    assert 'id="asset-form"' not in INDEX_HTML
    assert 'name="rubric_model"' not in INDEX_HTML


def test_protected_artifact_renderer_never_uses_supplied_preview() -> None:
    html = _run_frontend_expression(
        "formatArtifactPreview(TEST_PAYLOAD, 'rubric_extraction')",
        {
            "name": "protected_evaluation_guidelines.jsonl",
            "kind": "jsonl",
            "visibility": "protected_held_out",
            "preview_policy": "disabled",
            "preview": [{"criteria": ["RENDER-PROTECTED-CANARY"]}],
        },
    )

    assert "RENDER-PROTECTED-CANARY" not in html
    assert "Preview disabled" in html


def test_metadata_only_artifact_renderer_projects_safe_fields() -> None:
    html = _run_frontend_expression(
        "formatArtifactPreview(TEST_PAYLOAD, 'synthetic_coverage')",
        {
            "name": "derived_review_items.jsonl",
            "kind": "jsonl",
            "visibility": "audit_metadata",
            "preview_policy": "metadata_only",
            "preview": [
                {
                    "case_id": "case-1",
                    "fingerprint": "sha256:" + "2" * 64,
                    "status": "pending",
                    "user_input": "RENDER-METADATA-INPUT-CANARY",
                    "criteria": ["RENDER-METADATA-CRITERIA-CANARY"],
                    "case": {"input": "RENDER-METADATA-CASE-CANARY"},
                }
            ],
        },
    )

    assert "case-1" in html
    assert "sha256:" in html
    assert "pending" in html
    assert "RENDER-METADATA-INPUT-CANARY" not in html
    assert "RENDER-METADATA-CRITERIA-CANARY" not in html
    assert "RENDER-METADATA-CASE-CANARY" not in html


def test_review_panel_renders_only_safe_review_metadata() -> None:
    html = _run_frontend_expression(
        "renderReviewPanel(TEST_PAYLOAD.asset, TEST_PAYLOAD.review)",
        {
            "asset": {
                "asset_id": "v1",
                "state": {"status": "awaiting_review"},
            },
            "review": {
                "review_set_fingerprint": "sha256:" + "4" * 64,
                "counts": {"pending": 1, "approved": 0, "rejected": 0, "held": 1},
                "items": [
                    {
                        "review_item_id": "review-1",
                        "case_id": "case-1",
                        "fingerprint": "sha256:" + "2" * 64,
                        "status": "pending",
                        "reviewer": "RENDER-REVIEWER-CANARY",
                        "timestamp": "RENDER-TIMESTAMP-CANARY",
                        "user_input": "RENDER-REVIEW-INPUT-CANARY",
                        "criteria": ["RENDER-REVIEW-CRITERIA-CANARY"],
                        "provider_payload": {"body": "RENDER-PROVIDER-CANARY"},
                        "case": {"input": "RENDER-CASE-CANARY"},
                    }
                ],
                "held": [
                    {
                        "case_id": "case-2",
                        "fingerprint": "sha256:" + "3" * 64,
                        "status": "held",
                        "hold_reason": "conflicting_expected_truth",
                        "case": {"input": "RENDER-HELD-CANARY"},
                    }
                ],
            },
        },
    )

    assert "review-1" in html
    assert "case-1" in html
    assert "conflicting expected truth" in html
    assert "Finalize review and build datasets" in html
    assert 'data-review-case="case-1"' in html
    for canary in (
        "RENDER-REVIEW-INPUT-CANARY",
        "RENDER-REVIEW-CRITERIA-CANARY",
        "RENDER-PROVIDER-CANARY",
        "RENDER-CASE-CANARY",
        "RENDER-HELD-CANARY",
        "RENDER-REVIEWER-CANARY",
        "RENDER-TIMESTAMP-CANARY",
    ):
        assert canary not in html


def test_review_panel_renders_safe_decision_and_finalization_authority() -> None:
    html = _run_frontend_expression(
        "renderReviewPanel(TEST_PAYLOAD.asset, TEST_PAYLOAD.review)",
        {
            "asset": {"asset_id": "v1", "state": {"status": "released"}},
            "review": {
                "review_set_fingerprint": "sha256:" + "4" * 64,
                "counts": {
                    "pending": 0,
                    "approved": 1,
                    "rejected": 0,
                    "held": 0,
                },
                "items": [
                    {
                        "case_id": "case-1",
                        "fingerprint": "sha256:" + "2" * 64,
                        "trust_tier": "inferred_from_trusted_feedback",
                        "status": "approved",
                        "decision_id": "decision-1",
                        "dependency_fingerprint": "sha256:" + "5" * 64,
                        "context_fingerprint": "sha256:" + "6" * 64,
                        "truth_fingerprint": "sha256:" + "7" * 64,
                    }
                ],
                "held": [],
                "finalization": {
                    "finalization_id": "finalization-1",
                    "review_set_fingerprint": "sha256:" + "4" * 64,
                    "reviewer": "FINALIZATION-REVIEWER-CANARY",
                    "timestamp": "FINALIZATION-TIMESTAMP-CANARY",
                },
            },
        },
    )

    for safe_value in (
        "Inferred From Trusted Feedback",
        "decision-1",
        "finalization-1",
        "dependency sha256:",
        "context sha256:",
        "truth sha256:",
    ):
        assert safe_value in html
    assert "FINALIZATION-REVIEWER-CANARY" not in html
    assert "FINALIZATION-TIMESTAMP-CANARY" not in html


def test_review_panel_is_graceful_before_review_payload_arrives() -> None:
    html = _run_frontend_expression(
        "renderReviewPanel(TEST_PAYLOAD.asset, null)",
        {
            "asset": {
                "asset_id": "v1",
                "state": {"status": "awaiting_review"},
            }
        },
    )

    assert "Review queue is loading" in html
    assert "Finalize review and build datasets" not in html


def test_review_panel_pages_bounded_queue_without_rendering_bodies() -> None:
    html = _run_frontend_expression(
        "renderReviewPanel(TEST_PAYLOAD.asset, TEST_PAYLOAD.review)",
        {
            "asset": {"asset_id": "v1", "state": {"status": "awaiting_review"}},
            "review": {
                "review_set_fingerprint": "sha256:" + "4" * 64,
                "offset": 100,
                "limit": 100,
                "total": 201,
                "items": [],
                "held": [],
                "counts": {"pending": 201, "approved": 0, "rejected": 0, "held": 0},
            },
        },
    )

    assert 'data-review-page="0"' in html
    assert 'data-review-page="200"' in html
    assert "Previous review page" in html
    assert "Next review page" in html


def test_review_request_builders_bind_case_fingerprint_and_review_set() -> None:
    payload = json.loads(
        _run_frontend_expression(
            """JSON.stringify({
              decision: reviewDecisionRequest(
                'v1',
                {caseId:'case-1', fingerprint:'sha256:' + '2'.repeat(64)},
                'approved',
                'reviewer-name',
                'sha256:' + '4'.repeat(64)
              ),
              finalization: reviewFinalizationRequest(
                'v1', 'reviewer-name', 'sha256:' + '4'.repeat(64),
                'sha256:' + '8'.repeat(64)
              )
            })""",
            {},
        )
    )

    assert payload["decision"]["path"].endswith(
        "/reviews/sha256%3A" + "2" * 64 + "/approve"
    )
    assert json.loads(payload["decision"]["options"]["body"]) == {
        "case_id": "case-1",
        "reviewer": "reviewer-name",
        "expected_review_set_fingerprint": "sha256:" + "4" * 64,
    }
    assert payload["finalization"]["path"].endswith("/reviews/finalize")
    assert json.loads(payload["finalization"]["options"]["body"]) == {
        "reviewer": "reviewer-name",
        "expected_review_set_fingerprint": "sha256:" + "4" * 64,
        "expected_decision_set_fingerprint": "sha256:" + "8" * 64,
    }


def test_review_loader_requests_bounded_page_and_keeps_safe_response() -> None:
    result = json.loads(
        _run_frontend_expression(
            """(async () => {
              const calls = [];
              api = async (path, options) => {
                calls.push({path, options});
                return TEST_PAYLOAD.review;
              };
              APP.tenant = 'demo'; APP.assetId = 'v1';
              await loadReview('v1', 7, false);
              return JSON.stringify({calls, review: APP.reviewDetail, assetId: APP.reviewAssetId});
            })()""",
            {
                "review": {
                    "review_set_fingerprint": "sha256:" + "4" * 64,
                    "offset": 7,
                    "limit": 100,
                    "total": 1,
                    "items": [
                        {
                            "case_id": "case-1",
                            "fingerprint": "sha256:" + "2" * 64,
                            "status": "pending",
                        }
                    ],
                    "held": [],
                    "counts": {"pending": 1, "approved": 0, "rejected": 0, "held": 0},
                }
            },
        )
    )

    assert result["calls"] == [
        {
            "path": "/api/tenants/demo/evaluation-assets/v1/reviews?offset=7&limit=100",
            "options": None,
        }
    ]
    assert result["review"]["items"][0]["case_id"] == "case-1"
    assert result["assetId"] == "v1"


def test_review_loader_tracks_concurrent_requests_per_asset() -> None:
    result = json.loads(
        _run_frontend_expression(
            """(async () => {
              const resolvers = {};
              api = path => new Promise(resolve => {
                resolvers[path.includes('/asset-a/') ? 'a' : 'b'] = resolve;
              });
              APP.tenant = 'demo'; APP.assetId = 'asset-a';
              const first = loadReview('asset-a', 0, false);
              APP.assetId = 'asset-b';
              const second = loadReview('asset-b', 0, false);
              const during = [...APP.reviewLoadingAssets].sort();
              resolvers.a({items:[], held:[], counts:{}});
              resolvers.b({items:[], held:[], counts:{}});
              await Promise.all([first, second]);
              return JSON.stringify({
                during: during.map(value => JSON.parse(value)),
                remaining:[...APP.reviewLoadingAssets]
              });
            })()""",
            {},
        )
    )

    assert result == {
        "during": [["demo", "asset-a"], ["demo", "asset-b"]],
        "remaining": [],
    }


def test_review_decision_action_posts_exact_item_and_reloads_page() -> None:
    result = json.loads(
        _run_frontend_expression(
            """(async () => {
              const calls = [], reloads = [];
              globalThis.document = {getElementById: id => id === 'reviewer-name'
                ? {value:'reviewer-name'} : null};
              api = async (path, options) => { calls.push({path, options}); return {status:'approved'}; };
              loadReview = async (...args) => { reloads.push(args); };
              APP.tenant = 'demo'; APP.assetId = 'v1';
              APP.reviewDetail = {review_set_fingerprint:'sha256:' + '4'.repeat(64), offset:7};
              const button = {dataset:{reviewCase:'case-1', reviewFingerprint:'sha256:' + '2'.repeat(64),
                reviewDecision:'approved'}, disabled:false, textContent:'Approve'};
              await submitReviewDecision({asset_id:'v1'}, button);
              return JSON.stringify({calls, reloads, disabled:button.disabled});
            })()""",
            {},
        )
    )

    request = result["calls"][0]
    assert request["path"].endswith(
        "/reviews/sha256%3A" + "2" * 64 + "/approve"
    )
    assert json.loads(request["options"]["body"]) == {
        "case_id": "case-1",
        "reviewer": "reviewer-name",
        "expected_review_set_fingerprint": "sha256:" + "4" * 64,
    }
    assert result["reloads"] == [["v1", 7]]
    assert result["disabled"] is False


def test_review_finalization_posts_exact_set_clears_state_and_refreshes() -> None:
    result = json.loads(
        _run_frontend_expression(
            """(async () => {
              const calls = [], refreshes = [];
              globalThis.document = {getElementById: id => id === 'reviewer-name'
                ? {value:'reviewer-name'} : null};
              api = async (path, options) => { calls.push({path, options}); return {status:'running'}; };
              selectTenant = async tenant => { refreshes.push(tenant); };
              APP.tenant = 'demo'; APP.assetId = 'v1'; APP.reviewAssetId = 'v1';
              APP.reviewDetail = {
                review_set_fingerprint:'sha256:' + '4'.repeat(64),
                decision_set_fingerprint:'sha256:' + '8'.repeat(64)
              };
              const button = {disabled:false, textContent:'Finalize review and build datasets', title:''};
              await submitReviewFinalization({asset_id:'v1'}, button);
              return JSON.stringify({
                calls, refreshes, reviewDetail:APP.reviewDetail,
                reviewAssetId:APP.reviewAssetId, disabled:button.disabled,
                textContent:button.textContent, title:button.title
              });
            })()""",
            {},
        )
    )

    assert result["calls"] == [
        {
            "path": "/api/tenants/demo/evaluation-assets/v1/reviews/finalize",
            "options": {
                "method": "POST",
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(
                    {
                        "reviewer": "reviewer-name",
                        "expected_review_set_fingerprint": "sha256:" + "4" * 64,
                        "expected_decision_set_fingerprint": "sha256:" + "8" * 64,
                    },
                    separators=(",", ":"),
                ),
            },
        }
    ]
    assert result["refreshes"] == ["demo"]
    assert result["reviewDetail"] is None
    assert result["reviewAssetId"] is None
    assert result["disabled"] is False
    assert result["textContent"] == "Finalize review and build datasets"
    assert result["title"] == ""


def test_review_finalization_failure_preserves_state_and_restores_button() -> None:
    result = json.loads(
        _run_frontend_expression(
            """(async () => {
              const calls = [], refreshes = [];
              globalThis.document = {getElementById: id => id === 'reviewer-name'
                ? {value:'reviewer-name'} : null};
              api = async (path, options) => {
                calls.push({path, options}); throw new Error('stale review set');
              };
              selectTenant = async tenant => { refreshes.push(tenant); };
              APP.tenant = 'demo'; APP.assetId = 'v1'; APP.reviewAssetId = 'v1';
              APP.reviewDetail = {
                review_set_fingerprint:'sha256:' + '4'.repeat(64),
                decision_set_fingerprint:'sha256:' + '8'.repeat(64)
              };
              const button = {disabled:false, textContent:'Finalize review and build datasets', title:''};
              await submitReviewFinalization({asset_id:'v1'}, button);
              return JSON.stringify({
                calls, refreshes, reviewDetail:APP.reviewDetail,
                reviewAssetId:APP.reviewAssetId, disabled:button.disabled,
                textContent:button.textContent, title:button.title
              });
            })()""",
            {},
        )
    )

    assert result["calls"][0]["path"] == (
        "/api/tenants/demo/evaluation-assets/v1/reviews/finalize"
    )
    assert json.loads(result["calls"][0]["options"]["body"]) == {
        "reviewer": "reviewer-name",
        "expected_review_set_fingerprint": "sha256:" + "4" * 64,
        "expected_decision_set_fingerprint": "sha256:" + "8" * 64,
    }
    assert result["refreshes"] == []
    assert result["reviewDetail"] == {
        "review_set_fingerprint": "sha256:" + "4" * 64,
        "decision_set_fingerprint": "sha256:" + "8" * 64,
    }
    assert result["reviewAssetId"] == "v1"
    assert result["disabled"] is False
    assert result["textContent"] == "Finalize review and build datasets"
    assert result["title"] == "stale review set"


def test_split_seed_help_explains_stage_two_and_downstream_rebuild() -> None:
    html = _run_frontend_expression(
        "failedStageInputs(TEST_PAYLOAD, 'dataset_splits')",
        {"split_seed": 17},
    )

    assert "Changing this repartitions trusted feedback at Stage 2" in html
    assert "rebuilds downstream stages" in html
    assert "Changing this rebuilds Stage 8" not in html


def test_tenant_view_mounts_review_panel_while_awaiting_review() -> None:
    html = _run_frontend_expression(
        """(() => {
          const elements = new Map();
          const element = id => {
            if (!elements.has(id)) elements.set(id, {innerHTML:'', disabled:false});
            return elements.get(id);
          };
          globalThis.document = {getElementById: element, querySelectorAll: () => []};
          globalThis.history = {replaceState: () => {}};
          APP.tenant = 'demo';
          APP.assets = [TEST_PAYLOAD.asset];
          APP.assetId = 'v1';
          APP.stageKey = 'synthetic_coverage';
          APP.stageDetail = TEST_PAYLOAD.stage;
          APP.reviewTenant = 'demo';
          APP.reviewAssetId = 'v1';
          APP.reviewDetail = TEST_PAYLOAD.review;
          renderTenant();
          return element('main').innerHTML;
        })()""",
        {
            "asset": {
                "asset_id": "v1",
                "path": "evaluation_assets/v1",
                "runner_active": False,
                "config": {},
                "directories": {},
                "state": {
                    "status": "awaiting_review",
                    "current_stage": None,
                    "counts": {},
                    "stages": [
                        {
                            "stage": "synthetic_coverage",
                            "label": "Synthetic coverage",
                            "status": "completed",
                        },
                        {
                            "stage": "dataset_splits",
                            "label": "Dataset splits",
                            "status": "pending",
                        },
                    ],
                },
            },
            "stage": {
                "stage": "synthetic_coverage",
                "label": "Synthetic coverage",
                "status": "completed",
                "counts": {},
                "artifacts": [],
                "config": {"synthetic_coverage_enabled": False},
            },
            "review": {
                "review_set_fingerprint": "sha256:" + "4" * 64,
                "counts": {"pending": 1, "approved": 0, "rejected": 0, "held": 0},
                "items": [
                    {
                        "case_id": "case-1",
                        "fingerprint": "sha256:" + "2" * 64,
                        "status": "pending",
                        "case": {"input": "TENANT-REVIEW-BODY-CANARY"},
                    }
                ],
            },
        },
    )

    assert "Review derived cases" in html
    assert "case-1" in html
    assert "TENANT-REVIEW-BODY-CANARY" not in html


def test_cluster_inspector_renders_ids_without_representative_source_text() -> None:
    html = _run_frontend_expression(
        "clusterInspector(TEST_PAYLOAD, '#123456')",
        {
            "cluster_id": "cluster-1",
            "route": "route",
            "size": 2,
            "representative_ids": ["record-1", "record-2"],
            "representatives": ["CLUSTER-REPRESENTATIVE-CANARY"],
            "tools": ["CLUSTER-TOOL-CANARY"],
        },
    )

    assert "record-1" in html
    assert "record-2" in html
    assert "CLUSTER-REPRESENTATIVE-CANARY" not in html
    assert "CLUSTER-TOOL-CANARY" not in html


def test_awaiting_review_stage_cards_explain_the_pause_boundary() -> None:
    html = _run_frontend_expression(
        "stageCards(TEST_PAYLOAD)",
        {
            "state": {
                "status": "awaiting_review",
                "counts": {},
                "stages": [
                    {"stage": "synthetic_coverage", "status": "completed"},
                    {"stage": "dataset_splits", "status": "pending"},
                ],
            }
        },
    )

    assert "Review ready" in html
    assert "Waiting for finalization" in html


def test_asset_revision_changes_when_review_counts_change() -> None:
    changed = _run_frontend_expression(
        """assetRevision([{asset_id:'v1', state:{status:'awaiting_review', counts:{pending:1}}}])
          !== assetRevision([{asset_id:'v1', state:{status:'awaiting_review',
            counts:{pending:0, approved:1}}}])""",
        {},
    )

    assert changed == "true"


def test_tenant_asset_loader_ignores_stale_cross_tenant_completion() -> None:
    result = json.loads(
        _run_frontend_expression(
            """(async () => {
              const elements = new Map();
              const element = id => {
                if (!elements.has(id)) elements.set(id, {
                  innerHTML:'', disabled:false, classList:{toggle:() => {}}
                });
                return elements.get(id);
              };
              globalThis.document = {getElementById:element, querySelectorAll:() => []};
              globalThis.history = {replaceState:() => {}};
              loadStage = async () => {};
              APP.tenants = [{tenant_id:'alpha'}, {tenant_id:'beta'}];
              const resolvers = {};
              api = path => new Promise(resolve => {
                resolvers[path.includes('/alpha/') ? 'alpha' : 'beta'] = resolve;
              });
              const alpha = selectTenant('alpha');
              const beta = selectTenant('beta');
              resolvers.beta([TEST_PAYLOAD.beta]);
              await beta;
              resolvers.alpha([TEST_PAYLOAD.alpha]);
              await alpha;
              return JSON.stringify({
                tenant:APP.tenant,
                assetIds:APP.assets.map(asset => asset.asset_id),
                html:element('main').innerHTML,
                busy:APP.busy
              });
            })()""",
            {
                "alpha": {
                    "asset_id": "alpha-only",
                    "path": "evaluation_assets/alpha-only",
                    "state": {"status": "draft", "stages": [], "counts": {}},
                },
                "beta": {
                    "asset_id": "beta-only",
                    "path": "evaluation_assets/beta-only",
                    "state": {"status": "draft", "stages": [], "counts": {}},
                },
            },
        )
    )

    assert result["tenant"] == "beta"
    assert result["assetIds"] == ["beta-only"]
    assert "beta-only" in result["html"]
    assert "alpha-only" not in result["html"]
    assert result["busy"] is False


def test_review_loader_ignores_stale_cross_tenant_completion_for_same_asset() -> None:
    result = json.loads(
        _run_frontend_expression(
            """(async () => {
              const resolvers = {};
              api = path => new Promise(resolve => {
                resolvers[path.includes('/alpha/') ? 'alpha' : 'beta'] = resolve;
              });
              APP.tenant = 'alpha'; APP.assetId = 'v1';
              const alpha = loadReview('v1', 0, false);
              APP.tenant = 'beta'; APP.assetId = 'v1';
              const beta = loadReview('v1', 0, false);
              resolvers.beta({offset:0, items:[{case_id:'beta-case'}], held:[], counts:{}});
              await beta;
              resolvers.alpha({offset:0, items:[{case_id:'alpha-case'}], held:[], counts:{}});
              await alpha;
              return JSON.stringify({
                tenant:APP.reviewTenant,
                assetId:APP.reviewAssetId,
                caseId:APP.reviewDetail.items[0].case_id,
                loading:[...APP.reviewLoadingAssets]
              });
            })()""",
            {},
        )
    )

    assert result == {
        "tenant": "beta",
        "assetId": "v1",
        "caseId": "beta-case",
        "loading": [],
    }


def test_review_loader_ignores_reverse_order_older_page_completion() -> None:
    result = json.loads(
        _run_frontend_expression(
            """(async () => {
              const resolvers = {};
              api = path => new Promise(resolve => {
                resolvers[path.includes('offset=100') ? 'newer' : 'older'] = resolve;
              });
              APP.tenant = 'demo'; APP.assetId = 'v1';
              const older = loadReview('v1', 0, false);
              const newer = loadReview('v1', 100, false);
              resolvers.newer({offset:100, items:[{case_id:'newer-page'}], held:[], counts:{}});
              await newer;
              resolvers.older({offset:0, items:[{case_id:'older-page'}], held:[], counts:{}});
              await older;
              return JSON.stringify({
                offset:APP.reviewDetail.offset,
                caseId:APP.reviewDetail.items[0].case_id,
                loading:[...APP.reviewLoadingAssets]
              });
            })()""",
            {},
        )
    )

    assert result == {"offset": 100, "caseId": "newer-page", "loading": []}


def test_review_panel_disables_every_control_while_mutation_is_in_flight() -> None:
    html = _run_frontend_expression(
        """(() => {
          APP.tenant = 'demo';
          APP.reviewMutationStates.set(
            reviewRequestKey('demo', 'v1'), {inFlight:true, error:''}
          );
          return renderReviewPanel(TEST_PAYLOAD.asset, TEST_PAYLOAD.review);
        })()""",
        {
            "asset": {"asset_id": "v1", "state": {"status": "awaiting_review"}},
            "review": {
                "review_set_fingerprint": "sha256:" + "4" * 64,
                "decision_set_fingerprint": "sha256:" + "8" * 64,
                "offset": 100,
                "limit": 100,
                "total": 201,
                "counts": {"pending": 1, "approved": 0, "rejected": 0, "held": 0},
                "items": [
                    {
                        "case_id": "case-1",
                        "fingerprint": "sha256:" + "2" * 64,
                        "status": "pending",
                    }
                ],
                "held": [],
            },
        },
    )

    assert 'aria-busy="true"' in html
    assert re.search(r'data-review-decision="approved"[^>]*disabled', html)
    assert re.search(r'data-review-decision="rejected"[^>]*disabled', html)
    assert len(re.findall(r'data-review-page="[^"]+"[^>]*disabled', html)) == 2
    assert re.search(r'id="reviewer-name"[^>]*disabled', html)
    assert re.search(r'id="finalize-review"[^>]*disabled', html)


def test_review_decision_and_finalization_are_serialized_per_asset() -> None:
    result = json.loads(
        _run_frontend_expression(
            """(async () => {
              const calls = [];
              let resolveDecision;
              globalThis.document = {
                getElementById:id => id === 'reviewer-name' ? {value:'reviewer-name'} : null,
                querySelectorAll:() => []
              };
              api = (path, options) => {
                calls.push({path, options});
                return new Promise(resolve => { resolveDecision = resolve; });
              };
              loadReview = async () => {};
              APP.tenant = 'demo'; APP.assetId = 'v1';
              APP.reviewDetail = {
                review_set_fingerprint:'sha256:' + '4'.repeat(64),
                decision_set_fingerprint:'sha256:' + '8'.repeat(64), offset:0
              };
              const decisionButton = {dataset:{
                reviewCase:'case-1', reviewFingerprint:'sha256:' + '2'.repeat(64),
                reviewDecision:'approved'
              }, disabled:false, textContent:'Approve', title:''};
              const finalizeButton = {
                disabled:false, textContent:'Finalize review and build datasets', title:''
              };
              const decision = submitReviewDecision({asset_id:'v1'}, decisionButton);
              const finalization = submitReviewFinalization({asset_id:'v1'}, finalizeButton);
              const stateDuring = APP.reviewMutationStates.get(reviewRequestKey('demo','v1'));
              const callsDuring = calls.length;
              resolveDecision({status:'approved'});
              await Promise.all([decision, finalization]);
              return JSON.stringify({
                callsDuring, calls: calls.length,
                inFlightDuring:stateDuring.inFlight,
                finalState:APP.reviewMutationStates.get(reviewRequestKey('demo','v1'))
              });
            })()""",
            {},
        )
    )

    assert result["callsDuring"] == 1
    assert result["calls"] == 1
    assert result["inFlightDuring"] is True
    assert result["finalState"] == {"inFlight": False, "error": ""}


def test_review_mutation_error_survives_detached_button_rerender() -> None:
    result = json.loads(
        _run_frontend_expression(
            """(async () => {
              let rendered = '';
              const main = {};
              globalThis.document = {
                getElementById:id => id === 'reviewer-name' ? {value:'reviewer-name'}
                  : id === 'main' ? main : null,
                querySelectorAll:() => []
              };
              api = async () => { throw new Error('stale decision authority'); };
              APP.tenant = 'demo'; APP.assetId = 'v1';
              APP.reviewDetail = TEST_PAYLOAD.review;
              const asset = TEST_PAYLOAD.asset;
              renderTenant = () => { rendered = renderReviewPanel(asset, APP.reviewDetail); };
              const detachedButton = {dataset:{
                reviewCase:'case-1', reviewFingerprint:'sha256:' + '2'.repeat(64),
                reviewDecision:'approved'
              }, disabled:false, textContent:'Approve', title:''};
              await submitReviewDecision(asset, detachedButton);
              return JSON.stringify({
                rendered,
                state:APP.reviewMutationStates.get(reviewRequestKey('demo','v1')),
                detachedTitle:detachedButton.title
              });
            })()""",
            {
                "asset": {"asset_id": "v1", "state": {"status": "awaiting_review"}},
                "review": {
                    "review_set_fingerprint": "sha256:" + "4" * 64,
                    "decision_set_fingerprint": "sha256:" + "8" * 64,
                    "counts": {"pending": 1, "approved": 0, "rejected": 0, "held": 0},
                    "items": [
                        {
                            "case_id": "case-1",
                            "fingerprint": "sha256:" + "2" * 64,
                            "status": "pending",
                        }
                    ],
                    "held": [],
                },
            },
        )
    )

    assert result["state"] == {
        "inFlight": False,
        "error": "stale decision authority",
    }
    assert 'role="alert"' in result["rendered"]
    assert "stale decision authority" in result["rendered"]
    assert result["detachedTitle"] == "stale decision authority"


def test_released_asset_with_review_authority_loads_safe_finalization() -> None:
    result = json.loads(
        _run_frontend_expression(
            """(() => {
              const elements = new Map();
              const element = id => {
                if (!elements.has(id)) elements.set(id, {
                  innerHTML:'', disabled:false, classList:{toggle:() => {}}
                });
                return elements.get(id);
              };
              globalThis.document = {getElementById:element, querySelectorAll:() => []};
              globalThis.history = {replaceState:() => {}};
              const reviewLoads = [];
              loadStage = async () => {};
              loadReview = (...args) => { reviewLoads.push(args); return Promise.resolve(); };
              APP.tenant = 'demo'; APP.assets = [TEST_PAYLOAD.asset]; APP.assetId = 'v1';
              renderTenant();
              return JSON.stringify(reviewLoads);
            })()""",
            {
                "asset": {
                    "asset_id": "v1",
                    "path": "evaluation_assets/v1",
                    "review_authority_revision": "sha256:" + "9" * 64,
                    "state": {"status": "released", "stages": [], "counts": {}},
                }
            },
        )
    )

    assert result == [["v1"]]


def test_asset_revision_changes_when_review_authority_changes() -> None:
    changed = _run_frontend_expression(
        """assetRevision([{asset_id:'v1', review_authority_revision:'revision-1',
            state:{status:'awaiting_review'}}])
          !== assetRevision([{asset_id:'v1', review_authority_revision:'revision-2',
            state:{status:'awaiting_review'}}])""",
        {},
    )

    assert changed == "true"


def test_stage_methodology_copy_matches_enforced_non_probability_boundaries() -> None:
    html = EVALUATION_ASSET_HTML

    for claim in (
        "Select a deterministic centroid-nearest 10% of records within each unsupported cluster",
        "Non-probability acquisition",
        "Apply only mechanical schema, nonempty-context, scoreability, "
        "literal-leakage, and token-overlap checks",
        "Assign trusted groups to splits before guideline creation",
        "Publish finalized versioned tenant datasets",
    ):
        assert claim in html
    for false_claim in (
        "Sample 10% of unsupported clusters for labeling",
        "Run quality filters",
        "Reject unsafe or duplicate cases",
        "Reserve 20% of trusted groups for regression",
        "Split remaining cases globally by group",
    ):
        assert false_claim not in html
