# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.57

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.55
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 1.864 | 1.109 | 6.452 |
| call_untrusted | 3.657 | 1.821 | 12.530 |
| reconstruct_response | 2.020 | 1.320 | 5.668 |
| **Total** | **7.541** | **4.653** | **20.898** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 11 |
