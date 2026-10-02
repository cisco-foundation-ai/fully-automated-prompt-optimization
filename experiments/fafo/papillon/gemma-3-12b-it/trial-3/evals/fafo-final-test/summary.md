# Evaluation Summary

Total cases: 221

## Composite Score
- average: 94.95

## Score Breakdown
- leakage_fraction: 0.02
- privacy: 98.50
- quality: 91.40
- quality_passed: 0.91

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.005 | 1.451 | 10.749 |
| call_untrusted | 4.303 | 2.239 | 13.829 |
| reconstruct_response | 4.168 | 2.095 | 12.641 |
| **Total** | **11.476** | **7.060** | **38.357** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 25 |
