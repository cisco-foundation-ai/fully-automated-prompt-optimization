# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.14

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 95.69
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.925 | 1.374 | 18.646 |
| call_untrusted | 11.052 | 10.688 | 19.657 |
| reconstruct_response | 14.649 | 11.253 | 26.484 |
| **Total** | **29.626** | **24.852** | **57.951** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 14 |
