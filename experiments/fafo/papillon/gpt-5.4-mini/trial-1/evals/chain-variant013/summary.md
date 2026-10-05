# Evaluation Summary

Total cases: 111

## Composite Score
- average: 93.98

## Score Breakdown
- leakage_fraction: 0.07
- privacy: 93.37
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.390 | 1.223 | 8.141 |
| call_untrusted | 3.609 | 1.914 | 13.831 |
| reconstruct_response | 2.840 | 1.528 | 10.291 |
| **Total** | **8.839** | **5.063** | **27.808** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 17 |
