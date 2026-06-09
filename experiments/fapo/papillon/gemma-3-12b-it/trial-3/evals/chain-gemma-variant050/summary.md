# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.26

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.82
- quality: 93.69
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.657 | 1.339 | 18.114 |
| call_untrusted | 12.136 | 11.903 | 22.877 |
| reconstruct_response | 13.375 | 11.775 | 21.635 |
| **Total** | **29.167** | **26.914** | **50.390** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 15 |
