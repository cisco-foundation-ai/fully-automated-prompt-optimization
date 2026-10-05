# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.81

## Score Breakdown
- leakage_fraction: 0.08
- privacy: 92.32
- quality: 97.30
- quality_passed: 0.97

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 6.426 | 2.324 | 35.380 |
| call_untrusted | 7.145 | 3.960 | 24.333 |
| reconstruct_response | 7.575 | 4.043 | 25.232 |
| **Total** | **21.146** | **13.034** | **71.883** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 14 |
