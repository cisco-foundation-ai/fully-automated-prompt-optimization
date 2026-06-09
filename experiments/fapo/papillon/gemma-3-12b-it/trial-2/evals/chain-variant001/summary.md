# Evaluation Summary

Total cases: 111

## Composite Score
- average: 70.28

## Score Breakdown
- leakage_fraction: 0.58
- privacy: 42.37
- quality: 98.20
- quality_passed: 0.98

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 7.546 | 5.335 | 20.032 |
| call_untrusted | 6.241 | 5.401 | 16.133 |
| reconstruct_response | 9.882 | 9.598 | 18.668 |
| **Total** | **23.669** | **20.961** | **51.179** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 75 |
