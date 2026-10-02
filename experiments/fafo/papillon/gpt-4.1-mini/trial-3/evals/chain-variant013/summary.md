# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.33

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 96.07
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 4.288 | 1.842 | 20.360 |
| call_untrusted | 7.251 | 3.202 | 26.270 |
| reconstruct_response | 8.231 | 4.534 | 23.517 |
| **Total** | **19.770** | **11.372** | **58.394** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 13 |
