# Evaluation Summary

Total cases: 111

## Composite Score
- average: 97.08

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.87
- quality: 97.30
- quality_passed: 0.97

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.187 | 1.686 | 22.622 |
| call_untrusted | 7.965 | 3.277 | 29.119 |
| reconstruct_response | 7.470 | 3.443 | 31.402 |
| **Total** | **20.622** | **10.444** | **74.264** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 9 |
