<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Output ONLY search keywords. No explanation, no markdown, no quotes, no boolean operators. 2-5 keywords only.

User: Claim: ${claim}

Summary of first retrieval: ${steps.summarize_hop1.output}

Compare the claim to the summary. Identify a proper noun in the claim that is NOT mentioned in the summary. Use that proper noun plus 1-2 descriptive keywords as your search query.
