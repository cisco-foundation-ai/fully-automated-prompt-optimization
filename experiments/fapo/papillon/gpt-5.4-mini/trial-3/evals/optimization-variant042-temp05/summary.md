# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.27

## Score Breakdown
- leakage_fraction: 0.02
- privacy: 97.75
- quality: 92.79
- quality_passed: 0.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.491 | 1.219 | 8.227 |
| call_untrusted | 3.678 | 1.961 | 11.989 |
| reconstruct_response | 2.577 | 1.536 | 7.571 |
| **Total** | **8.745** | **5.898** | **22.583** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 13 |
