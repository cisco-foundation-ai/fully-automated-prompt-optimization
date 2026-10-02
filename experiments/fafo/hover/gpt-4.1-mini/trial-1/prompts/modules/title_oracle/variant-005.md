<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are identifying Wikipedia article titles needed to verify a multi-hop claim. You have access to passages already retrieved. Your task: figure out which specific Wikipedia articles are STILL MISSING from the retrieved set that would be needed to verify every part of the claim.

User: Claim: ${claim}

Passages already retrieved (showing article titles before the "|"):
${steps.retrieve_hop1.output}

${steps.retrieve_hop2.output}

${steps.retrieve_hop3.output}

Analysis from summaries:
${steps.summarize_hop1.output}
${steps.summarize_hop2.output}

Think step by step:
1. Break the claim into its component facts/connections
2. For each fact, check if the retrieved passages already cover it
3. Identify which connections are NOT yet supported by any retrieved article

For each missing connection, output the exact Wikipedia article title that would verify it. Use the format:
TITLE: <exact Wikipedia article title>

Include disambiguation in parentheses where needed (e.g., "The Swarm (roller coaster)", "Home on the Range (2004 film)").

Only list titles that are NOT already among the retrieved passages above. Output exactly 1-3 titles — only the ones you are most confident about.
