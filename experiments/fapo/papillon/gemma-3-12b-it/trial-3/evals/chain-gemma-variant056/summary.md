# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.86

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 96.22
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.751 | 1.268 | 20.084 |
| call_untrusted | 11.799 | 12.011 | 21.127 |
| reconstruct_response | 11.440 | 10.892 | 21.173 |
| **Total** | **26.990** | **26.228** | **52.737** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 12 |
