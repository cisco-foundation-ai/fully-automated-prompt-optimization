# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.71

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.82
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.751 | 1.402 | 18.560 |
| call_untrusted | 11.782 | 10.632 | 29.794 |
| reconstruct_response | 12.783 | 11.780 | 33.677 |
| **Total** | **28.316** | **25.759** | **65.900** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 12 |
