# Evaluation Summary

Total cases: 111

## Composite Score
- average: 73.33

## Score Breakdown
- leakage_fraction: 0.50
- privacy: 50.26
- quality: 96.40
- quality_passed: 0.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.704 | 2.778 | 18.888 |
| call_untrusted | 5.196 | 3.150 | 16.115 |
| reconstruct_response | 6.340 | 3.620 | 17.197 |
| **Total** | **17.240** | **12.626** | **53.345** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 64 |
