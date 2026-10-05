<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Output ONLY a search query. No explanation, no markdown, no quotes, no boolean operators. Just 2-5 keywords.

User: Claim: ${claim}

Summary of first search: ${steps.summarize_hop1.output}
Summary of second search: ${steps.summarize_hop2.output}

This is the third and final search. Read the claim carefully. Identify all proper nouns. Pick ONE that has NOT appeared in either summary above — especially entities in subordinate clauses, parenthetical descriptions, or toward the end of the claim. Write it as a 2-5 keyword search query.
