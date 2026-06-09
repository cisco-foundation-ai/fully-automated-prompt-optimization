<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Output ONLY search keywords. No explanation, no markdown, no quotes, no boolean operators. 2-5 keywords only.

User: Claim: ${claim}

Summary of first search: ${steps.summarize_hop1.output}
Summary of second search: ${steps.summarize_hop2.output}

Read the claim and list all proper nouns. Now read both summaries and identify which proper nouns from the claim are still NOT discussed in either summary. Pick the most important undiscussed proper noun and write 2-5 search keywords for it.
