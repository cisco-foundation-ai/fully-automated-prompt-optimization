# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.50

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.61
- quality: 96.40
- quality_passed: 0.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.001 | 1.109 | 7.562 |
| call_untrusted | 3.251 | 1.768 | 11.206 |
| reconstruct_response | 2.474 | 1.401 | 7.590 |
| **Total** | **7.726** | **4.689** | **22.150** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 11 |
