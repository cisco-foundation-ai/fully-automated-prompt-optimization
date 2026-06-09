<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You extract article titles and relevant facts from Wikipedia search results to support multi-hop claim verification.

User: Claim: ${claim}

Retrieved passages:
${steps.retrieve_hop1.output}

List the Wikipedia article titles from the passages above, then identify which entity or topic from the claim is still missing.

Format:
TITLES FOUND: [exact article titles from passages, comma-separated]
KEY FACTS: [1-2 sentences of relevant facts]
MISSING: [name of one entity/topic from the claim not yet found]
