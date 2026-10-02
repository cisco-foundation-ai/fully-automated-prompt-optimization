# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.26

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.82
- quality: 93.69
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.708 | 1.257 | 18.039 |
| call_untrusted | 12.746 | 12.578 | 25.453 |
| reconstruct_response | 11.964 | 11.987 | 24.836 |
| **Total** | **28.419** | **27.365** | **55.675** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 13 |
