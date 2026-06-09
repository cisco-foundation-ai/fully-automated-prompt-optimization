<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You identify which Wikipedia article is still needed to verify a claim. You will be given the claim and passages already retrieved.

User: Claim: ${claim}

Passages from first retrieval (hop 1):
${steps.retrieve_hop1.output}

Passages from second retrieval (hop 2):
${steps.retrieve_hop2.output}

The claim involves 3 Wikipedia articles. Look at the article titles in the passages above (the text before the | in each line). Determine which entity from the claim does NOT have its Wikipedia article among those retrieved.

Think step by step:
1. What are the 3 key entities/topics in this claim that would each have a Wikipedia article?
2. Which of those entities have a matching article title in the passages above?
3. Which one is MISSING?

End with exactly: MISSING: [the Wikipedia article title that needs to be found]
