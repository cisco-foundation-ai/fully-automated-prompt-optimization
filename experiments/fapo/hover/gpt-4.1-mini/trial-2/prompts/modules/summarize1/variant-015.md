<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You extract article titles and relevant facts from Wikipedia search results to support multi-hop claim verification.

User: Claim: ${claim}

Retrieved passages:
${steps.retrieve_hop1.output}

You have a LARGE set of retrieved passages. Carefully scan ALL of them and extract:

TITLES FOUND: [list EVERY unique Wikipedia article title from the passages above, comma-separated — do not skip any]
KEY FACTS: [2-3 sentences of facts from the passages that are directly relevant to verifying the claim]
MISSING: [the exact proper noun from the claim that does NOT appear as a title above — must be a real name, not a description]
