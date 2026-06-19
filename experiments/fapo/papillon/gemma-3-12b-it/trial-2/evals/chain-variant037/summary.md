# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.49

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 95.69
- quality: 97.30
- quality_passed: 0.97

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.725 | 1.212 | 18.763 |
| call_untrusted | 11.574 | 11.379 | 19.728 |
| reconstruct_response | 12.641 | 12.360 | 24.323 |
| **Total** | **27.940** | **26.235** | **58.987** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 11 |
