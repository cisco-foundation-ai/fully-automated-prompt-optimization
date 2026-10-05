# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.47

## Score Breakdown
- leakage_fraction: 0.02
- privacy: 98.35
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 1.737 | 0.955 | 4.500 |
| call_untrusted | 2.995 | 1.738 | 10.224 |
| reconstruct_response | 2.264 | 1.362 | 6.056 |
| **Total** | **6.995** | **4.481** | **23.677** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 9 |
