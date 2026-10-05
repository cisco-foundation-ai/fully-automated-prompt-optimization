<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You identify entities. Output format: Found: [list], Missing: [list], then NEXT SEARCH line.

User: Claim: ${claim}

Top retrieved article titles (from passage headers before "|"):
${steps.retrieve_hop1_trunc.output}

List the entities from the claim. Mark each FOUND (has matching article title above) or MISSING.

NEXT SEARCH: the single most important MISSING entity name
