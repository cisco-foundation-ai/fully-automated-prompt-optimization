# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.81

## Score Breakdown
- leakage_fraction: 0.07
- privacy: 93.22
- quality: 96.40
- quality_passed: 0.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 1.924 | 1.077 | 5.998 |
| call_untrusted | 3.840 | 1.935 | 15.435 |
| reconstruct_response | 2.850 | 1.507 | 10.257 |
| **Total** | **8.615** | **5.063** | **26.673** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 15 |
