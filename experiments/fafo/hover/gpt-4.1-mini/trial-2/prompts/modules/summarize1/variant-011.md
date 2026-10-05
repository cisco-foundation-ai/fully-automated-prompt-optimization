<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You extract article titles from Wikipedia search results.

User: Claim: ${claim}

Retrieved passages:
${steps.retrieve_hop1.output}

List the Wikipedia article titles from the passages above, then note any key facts relevant to the claim.

TITLES: [exact article titles, comma-separated]
FACTS: [1-2 relevant facts from passages]
