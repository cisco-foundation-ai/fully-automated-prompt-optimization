<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Extract proper nouns from passage TEXT that are NOT passage titles. These are entities mentioned WITHIN passages but not retrieved as their own article.

User: Claim: ${claim}

Passages retrieved so far:
${steps.retrieve_hop1.output}

${steps.retrieve_hop2.output}

List proper nouns (person, place, film, book, organization, event) that:
1. Appear in passage TEXT (after the | separator)
2. Are NOT the same as any passage title (before the | separator)
3. Could be their own Wikipedia article

One name per line. Maximum 10.
