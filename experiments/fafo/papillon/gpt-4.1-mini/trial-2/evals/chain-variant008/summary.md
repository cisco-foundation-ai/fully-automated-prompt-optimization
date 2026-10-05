# Evaluation Summary

Total cases: 111

## Composite Score
- average: 89.69

## Score Breakdown
- leakage_fraction: 0.08
- privacy: 91.99
- quality: 87.39
- quality_passed: 0.87

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.949 | 2.006 | 36.572 |
| call_untrusted | 6.046 | 3.242 | 15.131 |
| reconstruct_response | 5.102 | 2.371 | 15.712 |
| **Total** | **17.096** | **9.989** | **66.546** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 26 |
