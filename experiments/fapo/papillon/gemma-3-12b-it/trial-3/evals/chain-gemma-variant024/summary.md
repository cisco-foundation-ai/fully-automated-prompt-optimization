# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.75

## Score Breakdown
- leakage_fraction: 0.05
- privacy: 95.11
- quality: 96.40
- quality_passed: 0.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.602 | 1.414 | 18.594 |
| call_untrusted | 12.638 | 12.628 | 23.134 |
| reconstruct_response | 12.568 | 12.142 | 24.282 |
| **Total** | **28.808** | **28.260** | **54.443** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 12 |
