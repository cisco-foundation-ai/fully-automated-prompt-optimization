<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Pick the entity name from the list below that would help verify the claim. It must be different from previous queries.

User: Claim: ${claim}

What has been found so far:
${steps.summarize_hop2.output}

Names found in passages:
${steps.extract_entities.output}

Previous queries:
1. ${steps.query_hop3.output}
2. ${steps.query_hop3b.output}

Which name from the list above is most relevant to verifying the claim? Pick ONE name. Just the name, nothing else.
