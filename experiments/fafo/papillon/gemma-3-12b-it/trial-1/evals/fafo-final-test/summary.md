# Evaluation Summary

Total cases: 221

## Composite Score
- average: 96.72

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 96.16
- quality: 97.29
- quality_passed: 0.97

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.617 | 2.195 | 15.661 |
| call_untrusted | 18.384 | 17.270 | 29.089 |
| reconstruct_response | 18.672 | 17.592 | 27.983 |
| **Total** | **42.672** | **37.978** | **68.351** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 19 |
