# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.65

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 95.80
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.034 | 1.098 | 7.840 |
| call_untrusted | 3.991 | 1.820 | 15.332 |
| reconstruct_response | 2.579 | 1.434 | 9.344 |
| **Total** | **8.604** | **5.099** | **27.178** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 12 |
