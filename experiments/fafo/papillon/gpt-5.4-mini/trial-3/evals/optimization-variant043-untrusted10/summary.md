# Evaluation Summary

Total cases: 111

## Composite Score
- average: 97.22

## Score Breakdown
- leakage_fraction: 0.02
- privacy: 98.05
- quality: 96.40
- quality_passed: 0.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.296 | 1.311 | 8.027 |
| call_untrusted | 3.673 | 1.844 | 14.472 |
| reconstruct_response | 2.404 | 1.506 | 6.809 |
| **Total** | **8.373** | **4.925** | **22.498** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 8 |
