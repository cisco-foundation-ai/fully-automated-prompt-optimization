<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You generate the final Wikipedia search query for multi-hop claim verification. Two searches have been done.

User: Claim: ${claim}

Search 1 results:
${steps.summarize_hop1.output}

Search 2 results:
${steps.summarize_hop2.output}

Hop 2 searched for: ${steps.query_hop2.output}

Find the ONE remaining entity. Check:
1. Is there a proper noun in the claim not yet in TITLES FOUND? Use that.
2. If not, does the claim describe someone by role (e.g., "the star of X", "the director of Y", "the author of Z")? Look in KEY FACTS for their actual name.
3. Do NOT repeat "${steps.query_hop2.output}" or any title already found.

Output ONLY the name (1-5 words):
