<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Output ONLY search keywords. No explanation, no markdown, no quotes, no boolean operators. 2-5 keywords only.

User: Claim: ${claim}

Summary of first retrieval: ${steps.summarize_hop1.output}

Read the claim and count all distinct proper nouns (people, places, works, organizations). Now read the summary and identify which proper nouns from the claim are NOT yet discussed. Pick one that is not discussed and write 2-5 search keywords for it.
