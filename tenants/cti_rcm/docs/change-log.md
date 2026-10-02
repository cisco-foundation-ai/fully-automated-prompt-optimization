<!--
Copyright 2026 Cisco Systems, Inc. and its affiliates

SPDX-License-Identifier: Apache-2.0
-->

# Change Log

## 2026-04-01 — Foundation-Sec-8B-Instruct Prompt Optimization (dev set, 173 cases)

### Summary
Prompt-only optimization for Foundation-Sec-8B-Instruct (sagemaker) on CTIBench-RCM dev set. 30 variants tested (032-061). Best: variant-037 at 80.35% (baseline variant-001: 76.30%).

### Variant Progression (dev set)
| Variant | Score | answer_format | Strategy | Notes |
|---------|-------|---------------|----------|-------|
| 032 | 76.30% | 100.00% | Baseline (variant-001) on Instruct | Instruct baseline |
| 033 | 69.94% | 93.06% | NVD rules (from GPT-5 v005) | Rules HURT Instruct |
| 034 | 79.19% | 99.42% | Ultra-concise, no rules | Concise wins |
| 035 | 69.36% | 94.22% | Arrow-format rules + CWEs | More rules, more regression |
| 036 | 69.36% | 61.56% | Buffer overflow rule only | Destroyed format |
| **037** | **80.35%** | **100.00%** | **NVD convention mention, no rules** | **BEST** |
| 038 | 78.61% | 100.00% | CWE-ID only reply | Too terse |
| 039 | 66.47% | 72.54% | 037 + buffer rule | Rules destroy format |
| 040 | 80.35% | 99.71% | 034 + NVD inline | Tied best |
| 041 | 77.46% | 86.13% | NVD analyst role | Role hurt format |
| 042 | 78.03% | 100.00% | Root cause focus | Slightly worse |
| 043 | 79.77% | 99.42% | Parent CWE preference | Close |
| 044 | 78.61% | 97.69% | CWE-ID first | Format dip |
| 045 | 78.61% | 99.42% | Concise instruction | Neutral |
| 046 | 78.61% | 100.00% | "Most appropriate" wording | Neutral |
| 047 | 77.46% | 100.00% | Broader categories | Regressed |
| 048 | 79.77% | 100.00% | User prompt prefix | Close |
| 049 | 79.77% | 100.00% | Vulnerability analyst role | Close |
| 050 | 80.35% | 99.42% | Ablation: remove "root cause" | Tied best |
| 051 | 77.46% | 100.00% | Negative: no CWE-20 catch-all | Hurt |
| 052 | 79.19% | 100.00% | NVD reviewer role | Close |
| 053 | 75.14% | 98.27% | Structured format | Format constraint hurt |
| 054 | 80.35% | 98.55% | Class-first reasoning | Tied but worse format |
| 055 | 76.88% | 65.90% | No expert role | Role essential for format |
| 056 | 77.46% | 100.00% | CWE-ID only, no explanation | Too terse |
| 058 | 78.03% | 100.00% | "Consider class" wording | Neutral |
| 059 | 77.46% | 90.46% | Instructions in user message | Hurt format |
| 060 | 80.35% | 99.42% | Standard CWE hierarchy | Tied best |
| 061 | 73.41% | 96.53% | One-shot example | Examples hurt Instruct |

### Test Set Validation (827 cases)
| Variant | Test Score | Dev Score | Delta vs Baseline (test) |
|---------|-----------|-----------|--------------------------|
| 001 (baseline) | 68.68% | 76.30% | -- |
| **037 (best)** | **70.98%** | **80.35%** | **+2.30pp** |

Paper reference: Foundation-Sec-8B-Instruct = 70.4% on full 1000-case set.

### Key Findings for Instruct Model
- **Concise prompts win**: Any additional rules, examples, or structure HURTS the Instruct model.
- **NVD convention mention is sufficient**: Just saying "following NVD mapping conventions" activates the model's training knowledge without overriding it.
- **Format extraction is extremely fragile**: Specific CWE rules (e.g., "buffer overflow -> CWE-787") destroy answer_format extraction from 100% to 61-73%.
- **"CWE classification expert" role is essential**: Removing it drops format extraction to 65%.
- **The optimal prompt for Instruct is the OPPOSITE of GPT-5**: GPT-5 needed surgical NVD rules; Instruct works best with zero rules and a nudge.
- **Remaining failures**: CWE-787->CWE-121/122 (8 cases), CWE-404 confusion (3), CWE-798->CWE-20 (2), plus ~20 singleton confusions. These cannot be addressed via prompt without destroying format.

---

## 2026-04-01 — GPT-5 Prompt Optimization (dev set, 173 cases)

### Summary
Prompt-only optimization for GPT-5 on CTIBench-RCM dev set. 31 variants tested. Best: variant-029 at 85.55% (baseline variant-001: 78.61%).

### Variant Progression (dev set)
| Variant | Score | Strategy | Notes |
|---------|-------|----------|-------|
| 001 | 78.61% | Baseline | Simple classify prompt |
| 002 | 76.30% | Prefer parent CWE + examples | Regressed — too generic |
| 003 | 76.88% | Detailed abstraction rules | Regressed |
| 004 | 77.46% | NVD conventions explicit | Regressed, hurt answer_format |
| 005 | 82.66% | Surgical NVD rules (787, 77, 404, 798) | +4.05pp, best at the time |
| 006 | 81.50% | NVD analyst role + parent CWE | Good but less than 005 |
| 007 | 79.19% | CWE-787 rule only | Marginal gain, over-applies to CWE-121/120 |
| 008 | 78.03% | Softened buffer overflow rule | Lost benefit |
| 009 | 77.46% | CWE-798 + CWE-404 only | Slight loss |
| 010 | 78.03% | Soft buffer + all rules | Neutral |
| 011 | 78.61% | Nuanced stack/heap distinction | Tied baseline |
| 012 | 80.92% | CWE-787 + CWE-798 only | Removing CWE-77 hurt |
| 013 | 80.35% | 012 + frequency list | Frequency list didn't help |
| 014 | 76.30% | Step-by-step approach | Regressed, hurt answer_format |
| 015 | 81.50% | 005 minus CWE-404 rule | Slightly worse than 005 |
| 016 | 82.08% | 005 + verification step | Close but worse, hurt format |
| 017 | 79.77% | 005 + CWE-668/639 rules | Extra rules hurt |
| 018 | 82.08% | Concise arrow rules | Close to 005 |
| 019 | 82.66% | NVD analyst + comprehensive rules | Tied 005 |
| 020 | 83.24% | 005 + CWE-327/862 rules | New improvement |
| 021 | 80.35% | Ultra-concise, no justification | Short format hurt |
| 022 | 83.82% | 020 + more CWE rules (190,476,416) | New best |
| 023 | 83.82% | 022 + negative examples | Tied 022 |
| 024 | 83.24% | 022 + CWE-203/639 | Slightly worse |
| 025 | 79.19% | Shorter format + many rules | Regressed |
| 026 | 84.39% | 022 + neg examples + CWE-203/209 | New best |
| 027 | 83.24% | Minimal output-only format | Less than 026 |
| 028 | 83.24% | 022 + verification checklist | Tied 027 |
| 029 | 85.55% | 026 + refined CWE-404 wording | **BEST** |
| 030 | 84.97% | NVD analyst role + 029 rules | Close second |
| 031 | 83.82% | 029 + CWE-287/401 rules | Extra rules regressed |

### Test Set Validation (827 cases)
| Variant | Test Score | Dev Score | Delta vs Baseline (test) |
|---------|-----------|-----------|--------------------------|
| 001 (baseline) | 71.10% | 78.61% | — |
| 029 (best) | 76.06% | 85.55% | +4.96pp |

Paper reference: GPT-5 = 72.8% on full 1000-case set.

### Key Findings
- CWE-787 over-specification is the #1 failure (model maps "stack overflow" to CWE-121 instead of CWE-787 per NVD convention), but dataset also has cases labeled CWE-121 with identical descriptions — genuine label noise.
- Surgical NVD convention rules for specific CWE confusion pairs give the biggest gains.
- Adding too many rules introduces regressions from over-constraining.
- CWE-404 rule wording matters — "when there is no indication of memory corruption" worked best.
- Remaining ~25 failures are mostly label noise (7 buffer confusion) and genuinely ambiguous singletons.

## 2026-03-17
- Summary: Initial tenant setup with faith-based data loading and scoring.
- Why: Add CTI-CWE benchmark as a FAFO tenant for prompt optimization.
- Files/configs: Full tenant scaffold, `variant-001.md`, `local-classify-variant001.json`.
- Eval impact: Baseline 69.2% exact match (gpt-4.1-mini, 1000 cases).
- Rollback notes: N/A (initial setup).
