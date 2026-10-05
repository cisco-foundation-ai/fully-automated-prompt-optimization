<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are analyzing hop 4 retrieval results. Identify what the previous recovery attempt found and refine the search target.

User: Claim: ${claim}

Hop 4 retrieved passages:
${steps.retrieve_hop4.output}

Previous findings:
- Hop 1: ${steps.summarize_hop1.output}
- Hop 2: ${steps.summarize_hop2.output}
- Hop 3: ${steps.summarize_hop3.output}

Respond in this exact format:
FOUND: [ALL Wikipedia titles found across ALL hops]
STILL MISSING: [The entity still not found — name it precisely]
CLUES: [ALL accumulated clues plus any NEW clues from hop 4 passages — alternative names, spellings, related people/works]
NEXT TARGET: [Best alternative search approach based on ALL CLUES — must differ from previous queries]
