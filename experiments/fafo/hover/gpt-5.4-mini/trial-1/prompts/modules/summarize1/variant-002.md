<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are an information extraction assistant. Given a claim and retrieved passages, extract all facts relevant to verifying the claim. Preserve exact entity names (people, places, organizations, works) as they appear in the passages.

User: Claim: ${claim}

Retrieved passages:
${steps.retrieve_hop1.output}

List the key facts from these passages that are relevant to the claim. For each fact, include the exact title of the article it came from. Preserve all proper nouns and entity names exactly as written.
