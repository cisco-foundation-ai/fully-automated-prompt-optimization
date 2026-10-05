<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Answer the user's original query. A draft response from an assistant is provided for reference — it was generated without access to identifying details. Use it for inspiration but produce your own complete, high-quality answer that:
- Directly addresses the original query
- Uses all the specific names, places, and details from the original query
- Is helpful, accurate, and complete
- Matches the language of the original query

If the draft is already good, improve and personalize it with the original details. If the draft is poor or off-topic, ignore it and write your own answer.

User: Original query: ${query}

Draft for reference: ${steps.untrusted_response.output}
