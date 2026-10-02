# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.42

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.15
- quality: 93.69
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 6.538 | 2.261 | 30.223 |
| call_untrusted | 10.233 | 5.665 | 30.724 |
| reconstruct_response | 11.559 | 7.279 | 36.436 |
| **Total** | **28.330** | **17.632** | **97.007** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 11 |
