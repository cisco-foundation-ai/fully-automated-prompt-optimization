<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Extract and list every proper noun and named entity mentioned in the passages that relates to the claim. Include people, places, organizations, titles of works, dates, and events. Preserve exact spelling.

User: Claim: ${claim}

Retrieved passages:
${steps.retrieve_hop1.output}

List all proper nouns and named entities from these passages relevant to the claim. Then write one sentence summarizing the key relationship described.
