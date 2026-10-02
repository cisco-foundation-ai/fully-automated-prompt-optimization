<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are verifying a multi-hop claim. Your job is to identify which entity still needs its own Wikipedia article retrieved.

User: Claim: ${claim}

First retrieval summary:
${steps.summarize_hop1.output}

Second retrieval passages:
${steps.retrieve_hop2.output}

Step 1: List every proper noun in the claim (people, places, films, events, organizations).
Step 2: For each one, check if it appears as a FOUND TITLE or was retrieved.
Step 3: Name the one that has NOT been found yet.

If the missing entity is only DESCRIBED (not named) in the claim, look at the MENTIONED NAMES from the first retrieval for candidates.

Output: the missing entity's proper name. Never say "all found" or "N/A".
