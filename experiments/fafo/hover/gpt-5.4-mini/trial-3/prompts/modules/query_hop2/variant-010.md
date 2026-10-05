<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Output ONLY search keywords. No explanation, no markdown, no formatting, no quotes, no boolean operators. Keywords only.

User: Claim: ${claim}

Summary of first retrieval: ${steps.summarize_hop1.output}

The claim involves multiple entities. Some were already found. Generate a search query for an entity from the claim that is NOT discussed in the summary. Include the entity name plus 2-3 descriptive keywords to help find the right Wikipedia article. Output 3-7 keywords total.
