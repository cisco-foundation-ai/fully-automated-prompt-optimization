# Evaluation Summary

Total cases: 111

## Composite Score
- average: 93.55

## Score Breakdown
- leakage_fraction: 0.06
- privacy: 94.30
- quality: 92.79
- quality_passed: 0.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.340 | 1.213 | 8.916 |
| call_untrusted | 4.445 | 2.130 | 17.497 |
| reconstruct_response | 3.200 | 1.969 | 10.344 |
| **Total** | **9.985** | **6.772** | **27.223** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 20 |
