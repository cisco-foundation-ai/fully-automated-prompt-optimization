# Evaluation Summary

Total cases: 111

## Composite Score
- average: 93.23

## Score Breakdown
- leakage_fraction: 0.07
- privacy: 92.77
- quality: 93.69
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 1.878 | 1.091 | 6.757 |
| call_untrusted | 3.389 | 2.033 | 11.859 |
| reconstruct_response | 2.608 | 1.464 | 7.118 |
| **Total** | **7.875** | **4.588** | **20.701** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 20 |
