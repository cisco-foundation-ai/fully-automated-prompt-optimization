# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.09

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.68
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.551 | 1.278 | 16.804 |
| call_untrusted | 11.530 | 11.130 | 19.519 |
| reconstruct_response | 12.322 | 11.656 | 23.003 |
| **Total** | **27.403** | **25.430** | **51.104** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 12 |
