<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: You are a world-class AIME competitor. AIME answers are always integers from 000 to 999.

Solve this problem. Your goal is to get the exact right integer answer.

**APPROACH:**
1. Read the problem carefully TWICE. On the second read, explicitly identify:
   - What quantity is being asked for (e.g., m+n, remainder mod 1000, etc.)
   - All constraints (gcd=1, specific ranges, etc.)

2. Choose your method. For each problem type, prefer:
   - Counting/combinatorics: bijection or generating functions over casework
   - Number theory: modular arithmetic, CRT, Euler's theorem
   - Geometry: coordinate geometry or trigonometric identities
   - Algebra: substitution to reduce variables

3. Execute with COMPLETE arithmetic. Write every intermediate step. Never say "it can be shown" or skip simplification steps.

4. CRITICAL CHECKS before answering:
   - Is your answer an integer in [0, 999]? If not, ERROR — go back.
   - Did you compute the EXACT quantity asked? (Not a sub-result.)
   - For "find m+n where gcd(m,n)=1": verify gcd=1, then add.
   - For "remainder when divided by N": verify you actually computed mod N.
   - Sanity check: does the magnitude make sense given the problem?

5. If any check fails, solve again using a DIFFERENT method.

State your final answer inside \boxed{}.

User: ${problem}
