# Evaluation Summary

Total cases: 111

## Composite Score
- average: 69.74

## Score Breakdown
- leakage_fraction: 0.54
- privacy: 45.79
- quality: 93.69
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 6.037 | 2.989 | 21.762 |
| call_untrusted | 5.434 | 3.133 | 15.115 |
| reconstruct_response | 5.688 | 3.441 | 15.097 |
| **Total** | **17.158** | **11.985** | **52.088** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 72 |
