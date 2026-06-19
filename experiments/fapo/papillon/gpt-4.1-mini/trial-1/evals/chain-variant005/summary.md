# Evaluation Summary

Total cases: 111

## Composite Score
- average: 91.31

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.03
- quality: 85.59
- quality_passed: 0.86

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 4.709 | 1.803 | 20.166 |
| call_untrusted | 5.955 | 3.360 | 20.820 |
| reconstruct_response | 5.429 | 3.067 | 19.155 |
| **Total** | **16.093** | **10.431** | **49.697** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 22 |
