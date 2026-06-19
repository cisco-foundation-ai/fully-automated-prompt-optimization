# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.27

## Score Breakdown
- leakage_fraction: 0.00
- privacy: 99.55
- quality: 90.99
- quality_passed: 0.91

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 1.806 | 1.032 | 5.748 |
| call_untrusted | 2.820 | 1.637 | 9.358 |
| reconstruct_response | 1.735 | 1.189 | 4.909 |
| **Total** | **6.360** | **4.087** | **20.800** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 11 |
