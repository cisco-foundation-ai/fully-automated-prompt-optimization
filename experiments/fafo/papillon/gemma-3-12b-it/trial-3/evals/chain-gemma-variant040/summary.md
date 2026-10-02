# Evaluation Summary

Total cases: 111

## Composite Score
- average: 92.35

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 96.41
- quality: 88.29
- quality_passed: 0.88

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.372 | 1.228 | 17.834 |
| call_untrusted | 6.522 | 3.916 | 21.238 |
| reconstruct_response | 6.943 | 3.689 | 22.059 |
| **Total** | **16.837** | **10.281** | **48.084** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 21 |
