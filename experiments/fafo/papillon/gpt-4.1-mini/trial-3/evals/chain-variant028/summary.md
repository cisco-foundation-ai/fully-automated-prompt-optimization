# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.52

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.15
- quality: 91.89
- quality_passed: 0.92

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 6.093 | 2.099 | 30.046 |
| call_untrusted | 9.323 | 5.253 | 30.056 |
| reconstruct_response | 10.970 | 6.964 | 30.801 |
| **Total** | **26.385** | **16.532** | **82.193** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 14 |
