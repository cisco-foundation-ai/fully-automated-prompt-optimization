# Evaluation Summary

Total cases: 221

## Composite Score
- average: 67.02

## Score Breakdown
- leakage_fraction: 0.62
- privacy: 38.11
- quality: 95.93
- quality_passed: 0.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 8.077 | 5.283 | 18.797 |
| call_untrusted | 6.133 | 4.999 | 15.600 |
| reconstruct_response | 10.103 | 9.750 | 18.867 |
| **Total** | **24.312** | **21.084** | **46.611** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 158 |
