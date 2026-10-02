<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You extract article titles and relevant facts from Wikipedia search results to support multi-hop claim verification.

User: Claim: ${claim}

Retrieved passages:
${steps.retrieve_hop1.output}

List the Wikipedia article titles from the passages above. Then summarize which facts are relevant to verifying the claim.

TITLES FOUND: [exact article titles from passages, comma-separated]
KEY FACTS: [2-3 sentences of relevant facts from the passages that help verify the claim]
MISSING: [one proper noun from the claim that does NOT appear as an article title above — must be a specific name]
