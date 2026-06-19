<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You extract article titles and facts from Wikipedia search results.

User: Claim: ${claim}

Previous: ${steps.summarize_hop1.output}

New passages:
${steps.retrieve_hop2.output}

List all article titles found (both previous and new), then note facts from the new passages relevant to the claim.

TITLES: [all article titles, comma-separated]
FACTS: [key facts from new passages relevant to the claim]
