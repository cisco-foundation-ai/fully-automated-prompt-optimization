# Evaluation Summary

Total cases: 111

## Composite Score
- average: 93.91

## Score Breakdown
- leakage_fraction: 0.07
- privacy: 93.22
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 1.991 | 1.053 | 6.028 |
| call_untrusted | 3.596 | 1.994 | 11.473 |
| reconstruct_response | 2.713 | 1.548 | 8.846 |
| **Total** | **8.301** | **4.947** | **23.513** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 17 |
