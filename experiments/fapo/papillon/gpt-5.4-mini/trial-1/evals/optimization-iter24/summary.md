# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.44

## Score Breakdown
- leakage_fraction: 0.05
- privacy: 95.20
- quality: 93.69
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.488 | 1.139 | 7.941 |
| call_untrusted | 3.975 | 2.218 | 14.708 |
| reconstruct_response | 2.968 | 1.727 | 9.657 |
| **Total** | **9.430** | **5.647** | **29.397** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 15 |
