# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.11

## Score Breakdown
- leakage_fraction: 0.06
- privacy: 93.82
- quality: 96.40
- quality_passed: 0.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.965 | 1.483 | 19.261 |
| call_untrusted | 11.145 | 11.057 | 20.098 |
| reconstruct_response | 12.148 | 12.656 | 24.276 |
| **Total** | **27.258** | **28.768** | **52.966** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 15 |
