<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Output ONLY search keywords. No explanation, no markdown, no quotes, no boolean operators.

User: Claim: ${claim}

Summary of first retrieval: ${steps.summarize_hop1.output}

The claim involves multiple entities. Pick one entity (person, place, or work title) from the claim that the summary does NOT discuss. Write a search query using that entity's full name plus related keywords from the claim. Output 4-10 keywords.
