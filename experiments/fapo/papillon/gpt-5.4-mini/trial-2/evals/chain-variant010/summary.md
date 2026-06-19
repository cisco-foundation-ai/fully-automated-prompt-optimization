# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.52

## Score Breakdown
- leakage_fraction: 0.07
- privacy: 92.64
- quality: 96.40
- quality_passed: 0.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 1.978 | 1.064 | 6.423 |
| call_untrusted | 3.784 | 1.900 | 13.567 |
| reconstruct_response | 2.705 | 1.450 | 9.176 |
| **Total** | **8.467** | **5.187** | **23.502** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 15 |
