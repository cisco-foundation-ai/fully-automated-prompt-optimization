<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You identify which entities from a claim appear in retrieved passages.

User: Claim: ${claim}

Passages:
${steps.retrieve_hop1_trunc.output}

Which entities or topics from the claim are found in these passages? Which are still missing? Be brief.

NEXT SEARCH: output the exact name of a person, place, or thing from the claim that needs its own Wikipedia article found. Pick the one most likely to have a Wikipedia article.
