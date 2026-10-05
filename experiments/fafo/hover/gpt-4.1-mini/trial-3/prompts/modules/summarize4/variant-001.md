<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You analyze passages after FOUR retrieval rounds. At this point, if any entity is still missing, it requires careful deduction from accumulated evidence. Your job is to make your BEST GUESS at the specific Wikipedia article title of the remaining entity.

User: Claim: ${claim}

Prior analyses:
First: ${steps.summarize_hop1.output}
Second: ${steps.summarize_hop2.output}
Third: ${steps.summarize_hop3.output}

Fourth retrieval passages:
${steps.retrieve_hop4.output}

CRITICAL INSTRUCTIONS:
- If an entity is STILL missing after 4 rounds, use ALL accumulated facts to DEDUCE what it is
- The missing entity is almost certainly described indirectly in the claim via a relationship
- Check if any newly retrieved passage MENTIONS the missing entity by name (even in passing)
- Think about: What connects the found entities? What entity completes the relationship chain?

Output in this exact format:

FOUND ENTITIES: [ALL Wikipedia article titles found across all four rounds]
KEY FACTS: [1-2 facts that help identify the last missing entity — look for names mentioned in passages]
STILL NEEDED: [Your SPECIFIC BEST GUESS for the missing entity's Wikipedia article title. Use a real name, not a description. Write "None" if all entities are found]
