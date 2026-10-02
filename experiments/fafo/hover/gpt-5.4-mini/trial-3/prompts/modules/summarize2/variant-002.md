<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are a fact-checking assistant. Summarize the new passages, preserving every proper noun exactly.

User: Claim: ${claim}

What was found in the first search: ${steps.summarize_hop1.output}

New retrieved passages:
${steps.retrieve_hop2.output}

Instructions:
1. List every proper noun mentioned in the NEW passages.
2. For each, write one sentence about what the passages say.
3. Final line: "Still missing:" followed by proper nouns from the claim not yet found in either search.
