# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.63

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 96.47
- quality: 92.79
- quality_passed: 0.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.680 | 1.373 | 17.997 |
| call_untrusted | 12.057 | 11.852 | 22.646 |
| reconstruct_response | 11.474 | 11.251 | 23.123 |
| **Total** | **27.212** | **26.972** | **51.819** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 16 |
