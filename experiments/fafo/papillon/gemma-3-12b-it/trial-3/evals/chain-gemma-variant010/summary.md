# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.10

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.70
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.535 | 1.193 | 17.263 |
| call_untrusted | 11.645 | 11.674 | 22.215 |
| reconstruct_response | 11.565 | 11.241 | 22.883 |
| **Total** | **26.745** | **25.063** | **52.023** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 13 |
