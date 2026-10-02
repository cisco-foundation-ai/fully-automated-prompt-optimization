# Evaluation Summary

Total cases: 111

## Composite Score
- average: 93.92

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 95.95
- quality: 91.89
- quality_passed: 0.92

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.034 | 1.322 | 7.469 |
| call_untrusted | 3.865 | 2.054 | 15.350 |
| reconstruct_response | 2.639 | 1.453 | 9.972 |
| **Total** | **8.539** | **5.330** | **27.664** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 16 |
