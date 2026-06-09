# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.69

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.79
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.858 | 1.310 | 17.651 |
| call_untrusted | 13.590 | 13.773 | 24.217 |
| reconstruct_response | 14.762 | 14.931 | 25.162 |
| **Total** | **32.209** | **31.222** | **55.431** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 12 |
