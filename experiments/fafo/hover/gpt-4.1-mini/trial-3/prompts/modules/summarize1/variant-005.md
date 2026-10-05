<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You analyze a multi-hop claim by DECOMPOSING it into independent factual sub-claims, then checking which entities from each sub-claim were found in the retrieved passages.

User: Claim: ${claim}

Retrieved passages:
${steps.retrieve_hop1.output}

Step 1: Decompose the claim into 2-4 independent sub-claims. Each sub-claim should reference a specific entity.
Step 2: For each sub-claim, check if the relevant Wikipedia article was found in the passages.
Step 3: Identify which entities are STILL MISSING.

Output exactly this format:

CLAIM DECOMPOSITION:
- Sub-claim 1: [first atomic fact in the claim] → Entity: [entity name] → Found: [Yes/No]
- Sub-claim 2: [second atomic fact] → Entity: [entity name] → Found: [Yes/No]
- Sub-claim 3: [third atomic fact, if applicable] → Entity: [entity name] → Found: [Yes/No]

FOUND ENTITIES: [list specific Wikipedia article titles found that are relevant]
KEY FACTS: [2-3 facts that help identify the missing entities — especially relationships that reveal what the missing entity IS]
STILL NEEDED: [list the specific entity names from sub-claims marked "No" above. If an entity is described indirectly, write your best guess of its actual name]
