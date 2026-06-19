# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.67

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 96.04
- quality: 97.30
- quality_passed: 0.97

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.697 | 1.203 | 17.871 |
| call_untrusted | 15.615 | 15.987 | 23.192 |
| reconstruct_response | 16.555 | 16.297 | 26.944 |
| **Total** | **35.867** | **36.009** | **58.019** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 11 |
