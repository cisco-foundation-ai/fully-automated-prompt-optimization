# Evaluation Summary

Total cases: 111

## Composite Score
- average: 92.70

## Score Breakdown
- leakage_fraction: 0.10
- privacy: 89.90
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.996 | 2.461 | 22.924 |
| call_untrusted | 9.504 | 5.699 | 25.230 |
| reconstruct_response | 10.726 | 7.572 | 31.500 |
| **Total** | **26.226** | **19.003** | **79.347** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 23 |
