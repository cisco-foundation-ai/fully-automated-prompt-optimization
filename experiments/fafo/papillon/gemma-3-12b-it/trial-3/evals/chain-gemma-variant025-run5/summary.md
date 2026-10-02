# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.78

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.97
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 4.513 | 1.653 | 24.447 |
| call_untrusted | 15.457 | 12.883 | 36.604 |
| reconstruct_response | 14.583 | 12.095 | 35.545 |
| **Total** | **34.553** | **31.810** | **83.455** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 12 |
