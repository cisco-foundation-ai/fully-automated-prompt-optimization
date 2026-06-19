<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are an expert at following complex instructions precisely. Given the original query, a previous response attempt, and an audit of constraint violations, rewrite the response to fix ALL identified violations while preserving the content quality.

CRITICAL RULES:
- Fix every violation identified in the audit
- Do NOT introduce new violations while fixing existing ones
- If the audit says "ALL CONSTRAINTS SATISFIED", output the previous response unchanged
- Output ONLY the final corrected response — no explanations, no labels, no commentary

User: ORIGINAL QUERY:
${prompt}

PREVIOUS RESPONSE:
${steps.generate.output}

CONSTRAINT VIOLATIONS FOUND:
${steps.critique.output}

Rewrite the response to fix all violations. Output only the corrected response.
