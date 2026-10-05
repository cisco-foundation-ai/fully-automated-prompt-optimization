# Evaluation Summary

Total cases: 111

## Composite Score
- average: 92.28

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 96.28
- quality: 88.29
- quality_passed: 0.88

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.085 | 1.111 | 7.711 |
| call_untrusted | 3.612 | 2.136 | 11.881 |
| reconstruct_response | 2.419 | 1.531 | 6.882 |
| **Total** | **8.117** | **5.004** | **22.727** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 19 |
