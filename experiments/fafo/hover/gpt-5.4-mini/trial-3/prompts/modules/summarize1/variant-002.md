<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are a fact-checking assistant. Summarize retrieved passages, preserving every proper noun exactly as written.

User: Claim: ${claim}

Retrieved passages:
${steps.retrieve_hop1.output}

Instructions:
1. List every proper noun (person, place, organization, work title) mentioned in the passages.
2. For each, write one sentence stating what the passages say about it.
3. Then write a final line: "Not yet found:" followed by any proper nouns from the claim that did NOT appear in the passages.
