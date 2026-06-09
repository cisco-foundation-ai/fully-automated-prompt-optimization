# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.58

## Score Breakdown
- leakage_fraction: 0.05
- privacy: 94.56
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.507 | 1.349 | 8.798 |
| call_untrusted | 4.614 | 1.981 | 19.787 |
| reconstruct_response | 3.404 | 1.775 | 12.310 |
| **Total** | **10.526** | **6.188** | **33.173** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 17 |
