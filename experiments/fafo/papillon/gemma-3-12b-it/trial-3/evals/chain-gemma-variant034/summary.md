# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.38

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.27
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.449 | 1.300 | 16.750 |
| call_untrusted | 11.031 | 11.274 | 20.808 |
| reconstruct_response | 12.188 | 10.881 | 21.566 |
| **Total** | **26.668** | **24.137** | **51.222** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 10 |
