# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.65

## Score Breakdown
- leakage_fraction: 0.02
- privacy: 97.61
- quality: 93.69
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.436 | 1.238 | 13.245 |
| call_untrusted | 14.799 | 15.181 | 22.819 |
| reconstruct_response | 15.872 | 16.372 | 25.495 |
| **Total** | **34.107** | **34.578** | **56.285** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 13 |
