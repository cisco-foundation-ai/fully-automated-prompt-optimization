<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are identifying Wikipedia article titles needed to verify a multi-hop claim. This is a SECOND PASS — a first attempt already retrieved some articles. Your task: identify titles that are STILL missing.

User: Claim: ${claim}

All passages retrieved so far (showing article titles before the "|"):
${steps.retrieve_hop1.output}

${steps.retrieve_hop2.output}

${steps.retrieve_hop3.output}

${steps.retrieve_oracle.output}

Think step by step:
1. Break the claim into its component facts/connections
2. Check which parts of the claim are already covered by retrieved passages
3. Identify specific entities or facts still NOT covered

For each missing connection, output the exact Wikipedia article title. Use the format:
TITLE: <exact Wikipedia article title>

Include disambiguation in parentheses where needed. Focus on 1-3 titles you are most confident about. Only output titles NOT already in the retrieved passages above.
