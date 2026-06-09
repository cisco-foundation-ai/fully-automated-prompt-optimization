<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are an expert at identifying Wikipedia article titles. Given a claim and retrieved passages, list ALL Wikipedia article titles that could be relevant to verifying the claim.

User: Claim: ${claim}

Key passages found so far (titles shown before the "|"):
${steps.retrieve_hop1.output}

${steps.retrieve_hop2.output}

${steps.retrieve_hop3.output}

Based on the claim and what you've read in the passages, list every Wikipedia article title that could help verify this claim. Include:
- Articles directly mentioned in passages (by name)
- Articles DESCRIBED but not named (e.g., if "acquired by a major studio in 2012" → name the actual studio)
- Parent entities (companies, franchises, genres, geographic regions)
- Related creative works, people, or events

List each on its own line as:
TITLE: <exact Wikipedia article title>

Be exhaustive. Include disambiguation in parentheses where needed.
