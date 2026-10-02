# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.53

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 96.27
- quality: 92.79
- quality_passed: 0.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.594 | 1.568 | 32.776 |
| call_untrusted | 18.092 | 13.631 | 42.112 |
| reconstruct_response | 16.098 | 14.368 | 33.070 |
| **Total** | **39.783** | **34.773** | **83.791** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 16 |
