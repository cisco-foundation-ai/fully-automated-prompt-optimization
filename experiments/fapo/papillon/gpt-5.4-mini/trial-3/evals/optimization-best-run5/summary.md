# Evaluation Summary

Total cases: 111

## Composite Score
- average: 98.05

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.00
- quality: 99.10
- quality_passed: 0.99

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.063 | 1.144 | 6.036 |
| call_untrusted | 3.402 | 1.799 | 10.998 |
| reconstruct_response | 2.344 | 1.592 | 6.535 |
| **Total** | **7.809** | **4.785** | **26.739** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 6 |
