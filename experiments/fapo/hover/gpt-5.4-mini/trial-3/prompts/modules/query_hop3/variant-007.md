<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Output ONLY search keywords. No explanation, no markdown, no quotes, no boolean operators. 2-5 keywords only.

User: Claim: ${claim}

Summary of first search: ${steps.summarize_hop1.output}
Summary of second search: ${steps.summarize_hop2.output}

This is the last search. The claim has at least three entities. Two have been covered. Find the remaining entity — look especially near the end of the claim, in relative clauses, or in parenthetical descriptions. Write 2-5 search keywords for that entity.
