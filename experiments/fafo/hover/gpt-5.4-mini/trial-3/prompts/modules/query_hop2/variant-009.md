<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Output ONLY search keywords. No explanation, no markdown, no quotes, no boolean operators. 2-5 keywords only.

User: Claim: ${claim}

Summary of first retrieval: ${steps.summarize_hop1.output}

Find the person, place, or work title in the claim that the summary does NOT mention. Write their exact name as a search query (2-5 words). Add one descriptive word if the name alone is ambiguous.
