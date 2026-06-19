# Evaluation Summary

Total cases: 111

## Composite Score
- average: 92.38

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 96.47
- quality: 88.29
- quality_passed: 0.88

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 6.520 | 2.087 | 27.925 |
| call_untrusted | 7.066 | 3.108 | 24.060 |
| reconstruct_response | 7.762 | 4.046 | 27.198 |
| **Total** | **21.347** | **10.742** | **60.372** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 20 |
