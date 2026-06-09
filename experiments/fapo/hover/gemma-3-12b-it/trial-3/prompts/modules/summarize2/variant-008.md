<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are finding Wikipedia articles to verify a claim. Examine the passages below and identify proper nouns mentioned in the text that could be the name of the entity described but not yet found as a title.

User: Claim: ${claim}

Titles found in first retrieval:
${steps.summarize_hop1.output}

Second retrieval passages:
${steps.retrieve_hop2.output}

Look at the claim carefully. Identify which entity is DESCRIBED but its Wikipedia article title has NOT appeared yet. Then scan the passage text above for a proper noun that names that entity.

Output format:
STILL MISSING: [the proper noun name to search for next]
