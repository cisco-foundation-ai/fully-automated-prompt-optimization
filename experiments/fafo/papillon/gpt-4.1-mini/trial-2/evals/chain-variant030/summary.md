# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.03

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 95.66
- quality: 96.40
- quality_passed: 0.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 6.038 | 1.869 | 34.990 |
| call_untrusted | 8.786 | 3.805 | 26.766 |
| reconstruct_response | 8.589 | 4.519 | 33.470 |
| **Total** | **23.413** | **12.340** | **72.970** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 13 |
