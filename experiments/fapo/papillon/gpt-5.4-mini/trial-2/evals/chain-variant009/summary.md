# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.97

## Score Breakdown
- leakage_fraction: 0.06
- privacy: 94.44
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 1.895 | 1.007 | 6.906 |
| call_untrusted | 3.616 | 1.776 | 14.665 |
| reconstruct_response | 2.601 | 1.336 | 8.405 |
| **Total** | **8.113** | **4.453** | **26.096** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 13 |
