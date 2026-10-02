# Evaluation Summary

Total cases: 221

## Composite Score
- average: 66.44

## Score Breakdown
- leakage_fraction: 0.64
- privacy: 36.05
- quality: 96.83
- quality_passed: 0.97

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 7.866 | 5.596 | 20.288 |
| call_untrusted | 8.460 | 5.802 | 15.911 |
| reconstruct_response | 11.112 | 10.643 | 18.391 |
| **Total** | **27.437** | **22.278** | **48.825** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 161 |
