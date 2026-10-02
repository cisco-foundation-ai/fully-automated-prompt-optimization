# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.92

## Score Breakdown
- leakage_fraction: 0.05
- privacy: 95.26
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.676 | 1.258 | 17.754 |
| call_untrusted | 11.482 | 10.847 | 21.000 |
| reconstruct_response | 11.870 | 10.725 | 24.938 |
| **Total** | **27.027** | **25.045** | **50.550** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 14 |
