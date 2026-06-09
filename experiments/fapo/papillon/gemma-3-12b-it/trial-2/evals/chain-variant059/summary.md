# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.00

## Score Breakdown
- leakage_fraction: 0.05
- privacy: 95.41
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 4.183 | 1.462 | 17.978 |
| call_untrusted | 12.745 | 12.309 | 22.335 |
| reconstruct_response | 13.315 | 12.403 | 28.299 |
| **Total** | **30.243** | **27.218** | **66.591** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 15 |
