# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.52

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.15
- quality: 91.89
- quality_passed: 0.92

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 4.784 | 1.943 | 20.356 |
| call_untrusted | 6.678 | 2.988 | 24.109 |
| reconstruct_response | 6.079 | 3.073 | 22.261 |
| **Total** | **17.541** | **9.108** | **64.446** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 13 |
