<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Output ONLY search keywords. No explanation, no markdown, no quotes, no boolean operators. 2-5 keywords only.

User: Claim: ${claim}

Summary of first search: ${steps.summarize_hop1.output}
Summary of second search: ${steps.summarize_hop2.output}

This is the final search. Read the claim and find the THIRD most important proper noun — one that is different from what the first two searches focused on. It might be mentioned briefly, in a parenthetical, or at the end of the claim. Write 2-5 search keywords for this entity.
