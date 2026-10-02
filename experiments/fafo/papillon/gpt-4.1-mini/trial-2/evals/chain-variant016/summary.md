# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.44

## Score Breakdown
- leakage_fraction: 0.06
- privacy: 94.28
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.462 | 1.833 | 23.975 |
| call_untrusted | 5.996 | 3.370 | 18.283 |
| reconstruct_response | 5.633 | 3.468 | 16.384 |
| **Total** | **17.091** | **10.175** | **64.231** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 16 |
