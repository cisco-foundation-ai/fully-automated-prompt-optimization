# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.72

## Score Breakdown
- leakage_fraction: 0.06
- privacy: 93.95
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.334 | 1.630 | 27.584 |
| call_untrusted | 16.216 | 14.002 | 32.961 |
| reconstruct_response | 17.282 | 15.169 | 39.675 |
| **Total** | **38.832** | **33.482** | **91.297** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 16 |
