# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.00

## Score Breakdown
- leakage_fraction: 0.06
- privacy: 93.60
- quality: 96.40
- quality_passed: 0.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 1.773 | 1.128 | 6.401 |
| call_untrusted | 3.618 | 1.871 | 16.494 |
| reconstruct_response | 2.621 | 1.550 | 7.721 |
| **Total** | **8.012** | **4.818** | **27.365** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 15 |
