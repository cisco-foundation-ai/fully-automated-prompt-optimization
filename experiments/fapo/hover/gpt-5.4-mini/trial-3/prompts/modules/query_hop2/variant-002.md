<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Output ONLY a search query. No explanation, no markdown, no quotes, no boolean operators. Just 2-5 keywords.

User: Claim: ${claim}

Summary of what was already found: ${steps.summarize_hop1.output}

The claim mentions multiple entities. Some were found in the first search. Pick ONE entity from the claim that was NOT found yet — preferably the second or third most prominent proper noun (person, place, or title). Write it as a 2-5 keyword search query.
