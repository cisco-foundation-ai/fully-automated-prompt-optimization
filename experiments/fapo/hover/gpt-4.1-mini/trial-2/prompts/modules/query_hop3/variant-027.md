<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You generate the final Wikipedia search query for multi-hop claim verification.

User: Claim: ${claim}

Titles and facts found:
${steps.summarize_hop1.output}

${steps.summarize_hop2.output}

Raw passages from search 2:
${steps.retrieve_hop2.output}

Previous search: ${steps.query_hop2.output}

Find the ONE entity from the claim still missing. If the claim describes someone by role, check the passages above for their name. Do NOT repeat the previous search or any found title.

Output ONLY the entity name (1-5 words):
