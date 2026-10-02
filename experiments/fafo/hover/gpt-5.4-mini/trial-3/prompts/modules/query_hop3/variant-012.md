<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Output ONLY search keywords. No explanation, no markdown, no quotes, no boolean operators.

User: Claim: ${claim}

Summary of first search: ${steps.summarize_hop1.output}
Summary of second search: ${steps.summarize_hop2.output}

This is the final search. Find an entity from the claim that neither summary discusses — especially entities in subordinate clauses or near the end of the claim. Write a search query using that entity's full name plus related keywords. Output 4-10 keywords.
