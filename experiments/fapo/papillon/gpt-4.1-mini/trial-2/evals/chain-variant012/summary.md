# Evaluation Summary

Total cases: 111

## Composite Score
- average: 93.35

## Score Breakdown
- leakage_fraction: 0.08
- privacy: 92.10
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 4.116 | 1.570 | 16.937 |
| call_untrusted | 5.908 | 2.974 | 19.757 |
| reconstruct_response | 6.042 | 3.598 | 16.614 |
| **Total** | **16.066** | **9.635** | **51.725** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 18 |
