# Evaluation Summary

Total cases: 111

## Composite Score
- average: 92.63

## Score Breakdown
- leakage_fraction: 0.12
- privacy: 87.97
- quality: 97.30
- quality_passed: 0.97

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.266 | 1.845 | 24.213 |
| call_untrusted | 6.542 | 3.490 | 20.948 |
| reconstruct_response | 6.023 | 4.063 | 16.366 |
| **Total** | **17.831** | **8.852** | **65.256** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 21 |
