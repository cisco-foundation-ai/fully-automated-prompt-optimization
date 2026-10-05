# Evaluation Summary

Total cases: 221

## Composite Score
- average: 93.93

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 96.00
- quality: 91.86
- quality_passed: 0.92

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 1.991 | 1.182 | 6.774 |
| call_untrusted | 3.511 | 2.042 | 11.487 |
| reconstruct_response | 2.583 | 1.554 | 7.931 |
| **Total** | **8.085** | **5.759** | **25.370** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 33 |
