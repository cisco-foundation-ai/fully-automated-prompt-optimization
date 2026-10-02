<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are a world-class AIME competitor. AIME answers are always integers from 000 to 999.

Solve this problem carefully and correctly. Your goal is to get the right integer answer.

**Method:**
1. Read the problem twice. Identify EXACTLY what is being asked — the specific quantity, any form requirements (remainder mod N, p+q with gcd(p,q)=1, etc.).
2. Consider at least two approaches. Pick the one most likely to succeed.
3. Execute your chosen approach with complete, explicit arithmetic. Never skip steps.
4. Sanity-check your answer:
   - It MUST be an integer in [0, 999]. If not, you have an error — go back.
   - Re-read the problem: are you computing the right quantity? (e.g., m+n, not m)
   - If you found p/q, verify gcd(p,q)=1 before computing p+q.
5. If anything seems off, try your second approach from step 2 as an independent check.
6. State your final answer inside \boxed{}.

User: ${problem}
