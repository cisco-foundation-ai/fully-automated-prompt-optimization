# Evaluation Summary

Total cases: 111

## Composite Score
- average: 69.49

## Score Breakdown
- leakage_fraction: 0.52
- privacy: 47.98
- quality: 90.99
- quality_passed: 0.91

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.574 | 2.594 | 20.425 |
| call_untrusted | 5.318 | 3.328 | 14.382 |
| reconstruct_response | 5.674 | 3.552 | 16.165 |
| **Total** | **16.567** | **12.388** | **45.475** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 73 |
