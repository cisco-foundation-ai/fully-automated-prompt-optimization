# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.98

## Score Breakdown
- leakage_fraction: 0.05
- privacy: 94.67
- quality: 97.30
- quality_passed: 0.97

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.831 | 2.260 | 27.553 |
| call_untrusted | 7.201 | 4.990 | 20.856 |
| reconstruct_response | 8.057 | 6.254 | 21.005 |
| **Total** | **21.089** | **15.490** | **61.302** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 13 |
