<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Output ONLY search keywords. No explanation, no markdown, no quotes, no boolean operators. 2-5 keywords only.

User: Claim: ${claim}

Summary of first retrieval: ${steps.summarize_hop1.output}

The first search found some entities from the claim. Now find a DIFFERENT entity. Look at the claim and identify a proper noun (person name, place name, movie/book/song title, organization) that was NOT discussed in the summary. Copy that proper noun exactly from the claim and add 1-2 descriptive keywords. Output 2-5 keywords total.
