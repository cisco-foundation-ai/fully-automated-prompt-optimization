<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Output a different search query (1-5 words) to find the entity that is still missing. Try a different proper noun or angle than the previous search. Do not explain. Never output "N/A".

User: Claim: ${claim}

Previous searches found:
${steps.summarize_hop2.output}

Previous hop3 query was: ${steps.query_hop3.output}

Output a DIFFERENT search query targeting the same missing entity from a new angle. Just the query, nothing else.
