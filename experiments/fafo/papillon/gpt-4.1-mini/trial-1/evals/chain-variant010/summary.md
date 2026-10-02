# Evaluation Summary

Total cases: 111

## Composite Score
- average: 93.53

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.98
- quality: 90.09
- quality_passed: 0.90

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.405 | 1.795 | 26.567 |
| call_untrusted | 7.977 | 4.089 | 29.119 |
| reconstruct_response | 7.811 | 4.421 | 25.240 |
| **Total** | **21.192** | **12.672** | **79.953** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 17 |
