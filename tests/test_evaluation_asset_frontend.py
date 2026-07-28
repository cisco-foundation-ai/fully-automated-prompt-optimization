# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for the separate Evaluation Asset Studio frontend."""

from src.hephaestus.webui.evaluation_assets_frontend import EVALUATION_ASSET_HTML
from src.hephaestus.webui.frontend import INDEX_HTML


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
    assert 'name="match_threshold"' in EVALUATION_ASSET_HTML
    assert 'value="0.6"' in EVALUATION_ASSET_HTML
    assert 'name="synthetic_coverage_enabled"' in EVALUATION_ASSET_HTML
    assert 'name="synthetic_cases_per_cluster"' in EVALUATION_ASSET_HTML
    assert "Disabled" in EVALUATION_ASSET_HTML
    assert "raw feedback and unlabeled conversations" in EVALUATION_ASSET_HTML
    assert "Interactive clustering view" in EVALUATION_ASSET_HTML
    assert "Artifact guide" in EVALUATION_ASSET_HTML
    assert "renderArtifactMenu(artifacts)" in EVALUATION_ASSET_HTML
    assert "Representative traces to label" in EVALUATION_ASSET_HTML
    assert "Example data" in EVALUATION_ASSET_HTML
    assert "Report unsupported clusters" in EVALUATION_ASSET_HTML
    assert "Split all remaining provenance classes globally by group" in EVALUATION_ASSET_HTML
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


def test_explorer_links_to_studio_without_asset_form() -> None:
    assert 'href="/evaluation-assets/"' in INDEX_HTML
    assert 'class="studio-nav"' in INDEX_HTML
    assert "Open Evaluation Asset Studio" in INDEX_HTML
    assert 'id="asset-form"' not in INDEX_HTML
    assert 'name="rubric_model"' not in INDEX_HTML
