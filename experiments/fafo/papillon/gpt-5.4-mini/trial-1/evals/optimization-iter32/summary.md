# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.31

## Score Breakdown
- leakage_fraction: 0.06
- privacy: 94.02
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.144 | 1.179 | 7.733 |
| call_untrusted | 4.245 | 2.066 | 16.069 |
| reconstruct_response | 2.944 | 1.654 | 9.524 |
| **Total** | **9.333** | **5.386** | **27.607** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 18 |
