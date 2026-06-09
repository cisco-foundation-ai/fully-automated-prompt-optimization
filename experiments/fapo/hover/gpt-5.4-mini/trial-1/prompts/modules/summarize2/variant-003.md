<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are an information extraction assistant. Your job is to identify which entities from the claim have been found in passages and which are still missing.

User: Claim: ${claim}

Previously found (hop 1):
${steps.summarize_hop1.output}

New retrieved passages (hop 2):
${steps.retrieve_hop2.output}

Do the following:
1. List the article titles from the new passages that are relevant to the claim.
2. Combine with information from hop 1 to determine: which specific entities, events, or topics mentioned in the claim still do NOT have a matching Wikipedia article found?
3. For each missing entity, write its most likely Wikipedia article title. Wikipedia titles are typically the proper name of the entity (e.g., a person's full name, a film's title with disambiguation like "Film (year film)").

End your response with a line starting "MISSING:" followed by the most likely Wikipedia article title of the entity that still needs to be found.
