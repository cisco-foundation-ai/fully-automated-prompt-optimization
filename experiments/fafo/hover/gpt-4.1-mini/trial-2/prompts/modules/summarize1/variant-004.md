<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You help verify multi-hop claims by tracking which Wikipedia articles have been retrieved. Extract article titles from the passages and identify what entity from the claim still needs its own Wikipedia article retrieved.

User: Claim: ${claim}

Retrieved passages:
${steps.retrieve_hop1.output}

Instructions:
1. List the article titles that appear in the retrieved passages above.
2. Think about what distinct entities or topics the claim references that would each have their own Wikipedia article.
3. Identify which one of those entities does NOT yet have its article retrieved.

FOUND ARTICLES: [titles from passages, comma-separated]
CLAIM ENTITIES: [all distinct entities/topics in the claim that would have Wikipedia articles]
NOT YET RETRIEVED: [one specific entity name that needs to be searched next]
