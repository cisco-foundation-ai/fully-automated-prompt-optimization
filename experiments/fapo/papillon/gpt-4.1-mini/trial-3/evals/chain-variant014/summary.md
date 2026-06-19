# Evaluation Summary

Total cases: 111

## Composite Score
- average: 90.91

## Score Breakdown
- leakage_fraction: 0.05
- privacy: 95.33
- quality: 86.49
- quality_passed: 0.86

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.985 | 1.536 | 17.255 |
| call_untrusted | 6.459 | 3.881 | 20.994 |
| reconstruct_response | 6.361 | 4.162 | 21.439 |
| **Total** | **16.805** | **10.466** | **57.284** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 23 |
