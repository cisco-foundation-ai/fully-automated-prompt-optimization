# Evaluation Summary

Total cases: 111

## Composite Score
- average: 93.62

## Score Breakdown
- leakage_fraction: 0.06
- privacy: 94.44
- quality: 92.79
- quality_passed: 0.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.241 | 1.105 | 8.441 |
| call_untrusted | 3.044 | 1.874 | 9.888 |
| reconstruct_response | 2.367 | 1.376 | 7.352 |
| **Total** | **7.652** | **4.773** | **20.714** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 16 |
