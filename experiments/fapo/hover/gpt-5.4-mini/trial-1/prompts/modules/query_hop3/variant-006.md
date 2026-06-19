<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You output a Wikipedia article title to search for. Output ONLY the title, nothing else.

User: Claim: ${claim}

Evidence gathered so far:
${steps.summarize_hop1.output}

${steps.summarize_hop2.output}

The claim mentions multiple entities. Based on the evidence above, determine which entity from the claim has NOT yet been covered. Output that entity's most likely Wikipedia article title.

For people use their full proper name. For films include the year: "Title (YYYY film)". For TV shows: "Title (TV series)".

Output ONLY the article title. Nothing else. Never output placeholder text like {claim}.
