<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Output ONLY search keywords. No explanation, no markdown, no quotes, no boolean operators. 2-5 keywords only.

User: Claim: ${claim}

Summary of first retrieval: ${steps.summarize_hop1.output}

The claim mentions at least three entities. The first search likely covered the main subject. Now pick a DIFFERENT entity from the claim — specifically the second most important proper noun (person, place, work title, or organization). Write 2-5 search keywords for that entity only.
