# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.96

## Score Breakdown
- leakage_fraction: 0.07
- privacy: 92.63
- quality: 97.30
- quality_passed: 0.97

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.668 | 1.208 | 19.715 |
| call_untrusted | 11.946 | 11.302 | 27.347 |
| reconstruct_response | 12.749 | 12.416 | 23.486 |
| **Total** | **28.362** | **25.401** | **58.649** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 14 |
