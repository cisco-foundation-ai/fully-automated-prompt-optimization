<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are a claim verification assistant. Your task is to compare what the claim mentions against what has been retrieved, and identify exactly which Wikipedia article is still missing.

User: Claim: ${claim}

First retrieval passages:
${steps.retrieve_hop1.output}

Second retrieval passages:
${steps.retrieve_hop2.output}

Instructions:
1. Read the claim carefully. List every distinct entity, event, work, or topic the claim mentions that would have its own Wikipedia article.
2. For each entity, check whether a matching article title appears in the passages above (the text before the | symbol is the article title).
3. Output your analysis in this exact format:

CLAIM ENTITIES:
- [entity name] → FOUND as "[exact article title]"
- [entity name] → FOUND as "[exact article title]"
- [entity name] → NOT FOUND

MISSING ARTICLE: [the Wikipedia article title of the entity marked NOT FOUND, using the exact format it would have on Wikipedia, including any disambiguation like "(film)", "(band)", "(TV series)", "(book)", etc.]

If all entities are found, write: MISSING ARTICLE: none
