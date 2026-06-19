<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You extract article titles and relevant facts from Wikipedia search results to support multi-hop claim verification.

User: Claim: ${claim}

Retrieved passages:
${steps.retrieve_hop1.output}

List the Wikipedia article titles from the passages above. Then identify which proper noun from the claim (person, place, work, organization) still needs its own Wikipedia article retrieved.

TITLES FOUND: [exact article titles from passages, comma-separated]
KEY FACTS: [1-2 sentences of relevant facts from the passages]
MISSING: [the exact proper noun from the claim that is not in TITLES FOUND — must be a real name, not a description]
