# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.30

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 96.01
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.990 | 1.317 | 20.925 |
| call_untrusted | 11.691 | 11.324 | 21.214 |
| reconstruct_response | 12.835 | 12.770 | 25.003 |
| **Total** | **28.516** | **27.592** | **57.237** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 13 |
