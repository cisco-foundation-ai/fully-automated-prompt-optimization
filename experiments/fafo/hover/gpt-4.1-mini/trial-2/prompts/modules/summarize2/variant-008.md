<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Extract article titles and key facts from Wikipedia search results for claim verification.

User: Claim: ${claim}

Previous findings: ${steps.summarize_hop1.output}

New retrieved passages:
${steps.retrieve_hop2.output}

ALL TITLES: [all article titles from both rounds of search, comma-separated]
KEY FACT: [one sentence: the most important new fact from these passages that helps verify the claim]
MISSING: [one entity from the claim whose article was not retrieved yet, or "none"]
