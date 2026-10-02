# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.58

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.57
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.622 | 1.943 | 24.908 |
| call_untrusted | 8.636 | 4.635 | 21.970 |
| reconstruct_response | 9.532 | 5.295 | 31.303 |
| **Total** | **23.791** | **18.083** | **77.942** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 12 |
