<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You analyze passages after three retrieval rounds. By now, most entities have been found. Your job is to IDENTIFY THE EXACT NAME of any remaining missing entity using all accumulated evidence.

User: Claim: ${claim}

Prior analyses:
First: ${steps.summarize_hop1.output}
Second: ${steps.summarize_hop2.output}

Third retrieval passages:
${steps.retrieve_hop3.output}

CRITICAL: If an entity is still missing after 3 rounds of retrieval, it is likely referenced INDIRECTLY in the claim. Use all the facts you have gathered to DEDUCE its identity. Look for:
- Names mentioned in passages that connect to the claim but weren't listed as found
- Entities described by their relationship to found entities
- Alternate names or disambiguation variants

Output in this exact format:

FOUND ENTITIES: [ALL Wikipedia article titles found across all three rounds relevant to the claim]
KEY FACTS: [1-2 facts that help identify any remaining unknown entity]
STILL NEEDED: [Write the SPECIFIC NAMES of remaining entities. Make your BEST GUESS based on accumulated evidence. If the claim implies "the person who X" and your facts suggest it's "John Smith", write "John Smith". Write "None" only if truly all entities are found]
