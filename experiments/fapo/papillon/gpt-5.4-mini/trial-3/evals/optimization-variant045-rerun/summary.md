# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.87

## Score Breakdown
- leakage_fraction: 0.02
- privacy: 98.05
- quality: 93.69
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.110 | 1.122 | 7.897 |
| call_untrusted | 3.482 | 1.875 | 11.625 |
| reconstruct_response | 2.418 | 1.508 | 7.436 |
| **Total** | **8.011** | **5.069** | **23.385** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 11 |
