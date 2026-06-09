# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.18

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 95.77
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.574 | 1.690 | 23.639 |
| call_untrusted | 15.421 | 13.557 | 34.309 |
| reconstruct_response | 16.141 | 13.709 | 38.389 |
| **Total** | **37.135** | **33.275** | **81.566** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 14 |
