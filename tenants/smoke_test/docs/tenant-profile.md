<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Tenant Profile

## Organization Profile
smoke_test is a minimal integration-test tenant used to verify the FAFO eval pipeline end-to-end. It contains trivially easy yes/no questions so pipeline correctness can be validated without domain expertise.

## Security Environment Assumptions
- Input: simple factual yes/no questions with no sensitive content.
- Output: a single word ("yes" or "no").
- No external tool access required.

## Threat Model Focus
- Not applicable — this tenant exists solely for infrastructure validation, not security analysis.

## Known Safe Patterns
- Expected answers are always lowercase "yes" or "no".
- Questions are intentionally trivial and deterministic.

## Tenant Terminology
- **variant-001**: Known-bad baseline — no format constraint, LLM produces verbose answers, exact-match fails.
- **variant-002**: Known-good baseline — strict "yes or no" constraint, exact-match passes.
