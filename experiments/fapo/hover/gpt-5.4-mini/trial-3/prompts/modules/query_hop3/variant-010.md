<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Output ONLY search keywords. No explanation, no markdown, no formatting, no quotes, no boolean operators. Keywords only.

User: Claim: ${claim}

Summary of first search: ${steps.summarize_hop1.output}
Summary of second search: ${steps.summarize_hop2.output}

This is the final search. Find a proper noun from the claim that neither summary discusses. Focus on entities near the end of the claim or in subordinate clauses. Include the entity name plus 2-3 descriptive keywords. Output 3-7 keywords total.
