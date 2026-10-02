# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.50

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 96.42
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 6.372 | 2.141 | 31.070 |
| call_untrusted | 7.158 | 3.706 | 22.373 |
| reconstruct_response | 7.398 | 4.668 | 21.321 |
| **Total** | **20.928** | **12.488** | **67.482** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 13 |
