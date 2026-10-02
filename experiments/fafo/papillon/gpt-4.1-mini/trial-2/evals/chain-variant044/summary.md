# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.30

## Score Breakdown
- leakage_fraction: 0.05
- privacy: 95.10
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.062 | 2.257 | 23.798 |
| call_untrusted | 7.776 | 3.706 | 28.052 |
| reconstruct_response | 7.608 | 4.417 | 25.481 |
| **Total** | **20.445** | **11.129** | **67.290** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 14 |
