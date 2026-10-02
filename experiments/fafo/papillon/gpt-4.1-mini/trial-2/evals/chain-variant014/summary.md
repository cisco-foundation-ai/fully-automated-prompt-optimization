# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.39

## Score Breakdown
- leakage_fraction: 0.07
- privacy: 93.28
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 4.671 | 1.805 | 21.562 |
| call_untrusted | 6.348 | 3.728 | 19.677 |
| reconstruct_response | 6.374 | 3.245 | 24.159 |
| **Total** | **17.392** | **10.064** | **66.281** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 17 |
