# Evaluation Summary

Total cases: 111

## Composite Score
- average: 97.02

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.74
- quality: 97.30
- quality_passed: 0.97

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.569 | 1.286 | 18.856 |
| call_untrusted | 14.580 | 14.611 | 22.636 |
| reconstruct_response | 15.739 | 15.470 | 24.623 |
| **Total** | **33.887** | **33.342** | **55.540** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 10 |
