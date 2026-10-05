<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You identify entities. Output format: Found: [list], Missing: [list], then NEXT SEARCH line.

User: Claim: ${claim}

Prior: ${steps.summarize_hop2.output}

New article titles (from passage headers before "|"):
${steps.retrieve_hop3_trunc.output}

Update: which entities from the claim are FOUND vs MISSING now?

NEXT SEARCH: the single most important MISSING entity name
