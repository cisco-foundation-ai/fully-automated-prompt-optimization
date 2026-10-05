# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.17

## Score Breakdown
- leakage_fraction: 0.07
- privacy: 92.85
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.468 | 1.391 | 16.858 |
| call_untrusted | 12.706 | 11.825 | 23.675 |
| reconstruct_response | 13.531 | 12.855 | 27.673 |
| **Total** | **31.705** | **27.166** | **63.316** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 15 |
