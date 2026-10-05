<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Extract article titles and key facts from Wikipedia search results for claim verification.

User: Claim: ${claim}

Retrieved passages:
${steps.retrieve_hop1.output}

TITLES FOUND: [list article titles from the passages, comma-separated]
KEY FACT: [one sentence: the most important fact from these passages that helps verify the claim]
MISSING: [one entity from the claim whose article was not retrieved]
