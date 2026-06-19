<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You identify which entities from a claim appear in retrieved passages and extract search queries for missing entities.

User: Claim: ${claim}

Prior findings: ${steps.summarize_hop1.output}

New passages:
${steps.retrieve_hop2_trunc.output}

Which entities or topics from the claim are now found? Which are still missing? Be brief.

Important: some missing entities are referenced INDIRECTLY in the claim (e.g., "the director of X" or "the person who did Y"). If you can identify these entities from the passages above, name them.

NEXT SEARCHES: output up to 3 entity names to search for, one per line. Pick entities from the claim that still need their own Wikipedia article found.
