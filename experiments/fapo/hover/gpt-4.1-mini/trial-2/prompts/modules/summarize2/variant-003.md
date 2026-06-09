<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You extract article titles and relevant facts from Wikipedia search results to support multi-hop claim verification.

User: Claim: ${claim}

What was found in hop 1: ${steps.summarize_hop1.output}

New retrieved passages (hop 2):
${steps.retrieve_hop2.output}

List ALL Wikipedia article titles found so far (from both hops), then identify what is still missing.

Format:
TITLES FOUND: [ALL article titles from hop 1 AND hop 2, comma-separated]
KEY FACTS: [1-2 sentences of relevant facts from the new passages]
MISSING: [name of one entity/topic from the claim not yet found, or "none" if all covered]
