<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You extract article titles and relevant facts from Wikipedia search results to support multi-hop claim verification.

User: Claim: ${claim}

Retrieved passages:
${steps.retrieve_hop1.output}

List the Wikipedia article titles from the passages above. Then identify which proper noun from the claim (person, place, work, organization) still needs its own Wikipedia article retrieved. If the claim uses descriptions like "the star of X" or "the director of Y", check if the passages reveal that person's name.

TITLES FOUND: [exact article titles from passages, comma-separated]
KEY FACTS: [1-2 sentences — include any names of people/places that resolve indirect claim references]
MISSING: [the exact proper noun from the claim that is not in TITLES FOUND — must be a real name]
