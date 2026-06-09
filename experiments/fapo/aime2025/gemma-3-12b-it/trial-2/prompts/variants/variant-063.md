<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

System: Solve this math competition problem. The answer is an integer from 0 to 999.

Example of the expected approach:

Problem: Find the sum of all positive integers n less than 10 such that n^2 - 1 is divisible by 8.

Solution: We need n^2 ≡ 1 (mod 8). Testing values: n=1: 1≡1✓, n=2: 4≡4✗, n=3: 9≡1✓, n=4: 16≡0✗, n=5: 25≡1✓, n=6: 36≡4✗, n=7: 49≡1✓, n=8: 64≡0✗, n=9: 81≡1✓.
Sum = 1+3+5+7+9 = 25.
Verification: All odd numbers satisfy n^2≡1(mod 8) since (2k+1)^2 = 4k^2+4k+1 = 4k(k+1)+1, and k(k+1) is always even, so 4k(k+1) is divisible by 8. ✓
\boxed{25}

Now solve this problem. Show all work, verify your answer, and write it as \boxed{N}.

Important: Read the problem carefully. Make sure you understand what quantity is being asked for before you begin solving.

User: ${problem}
