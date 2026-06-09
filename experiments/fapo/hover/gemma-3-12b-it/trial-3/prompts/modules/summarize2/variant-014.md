<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are verifying a multi-hop claim. Identify the Wikipedia article that has NOT been found yet.

User: Claim: ${claim}

First retrieval summary:
${steps.summarize_hop1.output}

Second retrieval passages:
${steps.retrieve_hop2.output}

TASK: Find what's still missing.

Step 1: List every proper noun phrase in the claim (names, titles, places, events, dates, organizations).
Step 2: Check which ones appear as passage TITLES in the retrievals above.
Step 3: The one that does NOT appear as a title is the missing entity.

If you see a proper noun in the claim that is NOT a title of any retrieved passage, output that exact phrase. Even common-seeming phrases like "Song of the South" or "Computer security" can be Wikipedia article titles.

Output the missing entity name. Never say "all found" or "N/A".
