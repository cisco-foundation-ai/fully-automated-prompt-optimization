# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.89

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.00
- quality: 92.79
- quality_passed: 0.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.175 | 1.678 | 25.090 |
| call_untrusted | 6.901 | 3.288 | 23.000 |
| reconstruct_response | 6.395 | 3.354 | 24.692 |
| **Total** | **18.472** | **9.115** | **65.606** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 14 |
