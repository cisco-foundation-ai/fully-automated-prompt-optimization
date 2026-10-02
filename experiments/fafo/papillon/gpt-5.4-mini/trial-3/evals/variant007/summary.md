# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.95

## Score Breakdown
- leakage_fraction: 0.00
- privacy: 100.00
- quality: 91.89
- quality_passed: 0.92

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 1.688 | 0.989 | 6.629 |
| call_untrusted | 3.181 | 1.704 | 9.676 |
| reconstruct_response | 2.339 | 1.352 | 7.333 |
| **Total** | **7.208** | **4.318** | **20.240** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 9 |
