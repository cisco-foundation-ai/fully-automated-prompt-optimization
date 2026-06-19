# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.60

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.61
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 1.643 | 1.017 | 6.603 |
| call_untrusted | 3.081 | 1.600 | 11.835 |
| reconstruct_response | 2.068 | 1.244 | 6.543 |
| **Total** | **6.792** | **4.025** | **20.898** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 13 |
