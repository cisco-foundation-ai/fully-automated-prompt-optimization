<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Output ONLY search keywords. No explanation, no markdown, no quotes, no boolean operators. 2-5 keywords only.

User: Claim: ${claim}

Summary of first retrieval: ${steps.summarize_hop1.output}

The claim mentions at least three entities. The first search found some. Now pick a different proper noun from the claim — a person, place, work title, or event that the summary above did NOT cover. Write 2-5 search keywords using that entity's name.
