# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.42

## Score Breakdown
- leakage_fraction: 0.06
- privacy: 93.54
- quality: 97.30
- quality_passed: 0.97

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.511 | 1.155 | 8.812 |
| call_untrusted | 4.229 | 2.637 | 15.909 |
| reconstruct_response | 3.279 | 1.886 | 10.562 |
| **Total** | **10.018** | **6.294** | **30.592** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 15 |
