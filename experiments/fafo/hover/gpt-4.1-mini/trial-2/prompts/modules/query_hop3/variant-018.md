<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You search Wikipedia for claim verification. Two searches have already been done. You need one more article.

User: Claim: ${claim}

Articles found so far:
${steps.summarize_hop2.output}

Previous search query: ${steps.query_hop2.output}

Look at the proper nouns in the claim (person, place, film, band, event). Find one that is NOT in the titles above. Do NOT repeat "${steps.query_hop2.output}". Output ONLY that name (1-5 words):
