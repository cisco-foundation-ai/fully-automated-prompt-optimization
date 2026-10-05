# Evaluation Summary

Total cases: 111

## Composite Score
- average: 93.87

## Score Breakdown
- leakage_fraction: 0.08
- privacy: 92.24
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.857 | 2.095 | 32.501 |
| call_untrusted | 6.384 | 4.123 | 20.780 |
| reconstruct_response | 6.657 | 3.589 | 23.232 |
| **Total** | **18.898** | **10.821** | **58.144** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 18 |
