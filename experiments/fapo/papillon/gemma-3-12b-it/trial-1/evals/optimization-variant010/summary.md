# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.19

## Score Breakdown
- leakage_fraction: 0.05
- privacy: 94.68
- quality: 93.69
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.682 | 1.267 | 17.029 |
| call_untrusted | 12.013 | 11.997 | 27.464 |
| reconstruct_response | 11.161 | 9.149 | 28.159 |
| **Total** | **26.857** | **24.799** | **59.970** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 16 |
