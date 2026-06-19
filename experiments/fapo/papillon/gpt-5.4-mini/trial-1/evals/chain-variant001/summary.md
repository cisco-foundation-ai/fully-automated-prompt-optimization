# Evaluation Summary

Total cases: 111

## Composite Score
- average: 86.63

## Score Breakdown
- leakage_fraction: 0.20
- privacy: 79.57
- quality: 93.69
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.306 | 1.348 | 8.124 |
| call_untrusted | 3.652 | 1.947 | 12.688 |
| reconstruct_response | 2.787 | 1.522 | 9.962 |
| **Total** | **8.745** | **5.136** | **27.072** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 35 |
