<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You generate the FINAL Wikipedia search query for claim verification. Three searches have been done.

User: Claim: ${claim}

All findings so far: ${steps.summarize_hop3.output}

Previous searches: "${steps.query_hop2.output}", "${steps.query_hop3.output}"

Find the ONE remaining entity from the claim not yet in TITLES FOUND. If the claim describes someone by role, use KEY FACTS to find their actual name. Do NOT repeat previous searches or found titles.

Output ONLY the entity name (1-5 words):
