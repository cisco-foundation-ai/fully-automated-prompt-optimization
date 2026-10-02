# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.65

## Score Breakdown
- leakage_fraction: 0.01
- privacy: 99.40
- quality: 91.89
- quality_passed: 0.92

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.099 | 1.100 | 5.992 |
| call_untrusted | 3.118 | 1.748 | 10.107 |
| reconstruct_response | 2.518 | 1.493 | 8.479 |
| **Total** | **7.736** | **4.820** | **24.072** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 11 |
