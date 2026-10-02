# Evaluation Summary

Total cases: 221

## Composite Score
- average: 93.48

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 96.46
- quality: 90.50
- quality_passed: 0.90

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.471 | 1.573 | 11.530 |
| call_untrusted | 5.068 | 2.723 | 13.237 |
| reconstruct_response | 5.662 | 3.472 | 16.941 |
| **Total** | **14.201** | **9.558** | **44.657** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 35 |
