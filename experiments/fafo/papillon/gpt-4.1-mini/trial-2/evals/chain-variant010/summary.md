# Evaluation Summary

Total cases: 111

## Composite Score
- average: 91.27

## Score Breakdown
- leakage_fraction: 0.10
- privacy: 89.74
- quality: 92.79
- quality_passed: 0.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 6.503 | 1.947 | 30.687 |
| call_untrusted | 6.743 | 4.469 | 22.283 |
| reconstruct_response | 6.732 | 3.836 | 18.105 |
| **Total** | **19.978** | **12.818** | **65.949** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 23 |
