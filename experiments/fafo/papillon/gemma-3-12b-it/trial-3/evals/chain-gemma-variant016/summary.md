# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.01

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.52
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.482 | 1.174 | 16.112 |
| call_untrusted | 11.356 | 11.496 | 22.134 |
| reconstruct_response | 11.056 | 11.050 | 23.002 |
| **Total** | **25.894** | **24.655** | **48.505** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 12 |
