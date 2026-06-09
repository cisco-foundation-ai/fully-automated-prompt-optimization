# Evaluation Summary

Total cases: 111

## Composite Score
- average: 93.89

## Score Breakdown
- leakage_fraction: 0.08
- privacy: 92.29
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 6.459 | 2.431 | 32.411 |
| call_untrusted | 7.065 | 3.645 | 18.919 |
| reconstruct_response | 6.989 | 4.597 | 19.575 |
| **Total** | **20.513** | **13.527** | **69.288** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 18 |
