<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are an entity extraction specialist. Your job is to identify Wikipedia article titles AND entity names found in retrieved passages.

User: Claim: ${claim}

Retrieved passages:
${steps.retrieve_hop1.output}

List the Wikipedia article titles from the retrieved passages that are relevant to verifying this claim. Also scan the passage TEXT for proper nouns (people, places, films, books, organizations, events) that are mentioned but are NOT passage titles themselves.

Use this exact format:

FOUND TITLES: [list each relevant title on its own line]
MENTIONED NAMES: [list proper nouns from passage text that relate to the claim but are NOT passage titles]
NEXT SEARCH: [one proper noun or entity from the claim that was NOT found in any passage title]

You must ALWAYS output a NEXT SEARCH entity. Never output "none" or "N/A".
