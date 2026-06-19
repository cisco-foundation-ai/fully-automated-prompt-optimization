<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You extract article titles and facts from Wikipedia search results for multi-hop claim verification.

User: Claim: ${claim}

What was found in hop 1: ${steps.summarize_hop1.output}

New retrieved passages (hop 2):
${steps.retrieve_hop2.output}

List ALL article titles found so far. Then note any person, place, or work named in the passages that the claim refers to indirectly (e.g., if the claim says "the director of X" and the passages say "directed by John Smith", note "John Smith").

TITLES FOUND: [all article titles from both hops, comma-separated]
KEY FACTS: [facts from new passages, especially names of people/things that the claim references indirectly]
MISSING: [the proper noun from the claim not yet in TITLES FOUND, OR a name from KEY FACTS that resolves an indirect claim reference — must be a specific name, not "none"]
