<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Summarize the relevant information from the retrieved passages that helps verify the claim. Preserve all proper names exactly as they appear.

User: Claim: ${claim}

Retrieved passages:
${steps.retrieve_hop1.output}

First, list the article titles from the passages above (just the titles before the | character).
Then summarize what these articles tell us about the claim.
