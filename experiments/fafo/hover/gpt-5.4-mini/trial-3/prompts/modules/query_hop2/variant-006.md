<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Output ONLY search keywords. No explanation, no markdown, no quotes, no boolean operators. 2-5 keywords only.

User: Claim: ${claim}

Summary of first retrieval: ${steps.summarize_hop1.output}

The claim connects multiple entities through relationships. The first search covered some entities. Now search for a different entity mentioned in the claim — one that the first search did not cover. Pick a person, place, event, or title from the claim and write 2-5 search keywords for it.
