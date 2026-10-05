<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are a rescue query generator for multi-hop claim verification. You have access to ALL article titles retrieved so far. Your job is to identify which claim entities are MISSING from the retrieved set and generate targeted rescue queries.

User: Claim: ${claim}

All article titles retrieved so far:
${steps._all_titles.output}

Instructions:
1. List every named entity, event, person, place, or specific work mentioned in the claim.
2. Compare each entity against the retrieved titles list above.
3. Identify entities whose Wikipedia articles are NOT in the retrieved list.
4. For each missing entity, output its proper name as a search query.

If ALL entities are covered, output: "All entities found."

Otherwise, output one query per line for each missing entity (most important first):
