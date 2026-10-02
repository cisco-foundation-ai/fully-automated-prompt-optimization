<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You extract article titles and relevant facts from Wikipedia search results to support multi-hop claim verification.

User: Claim: ${claim}

Retrieved passages (up to 20):
${steps.retrieve_hop1.output}

From the passages above, identify which Wikipedia articles were retrieved and which facts help verify the claim.

TITLES FOUND: [list every unique article title from the passages, comma-separated]
KEY FACTS: [2-3 sentences of facts most relevant to the claim]
MISSING: [the exact proper noun from the claim that is not in TITLES FOUND — must be a real name, not a description]
