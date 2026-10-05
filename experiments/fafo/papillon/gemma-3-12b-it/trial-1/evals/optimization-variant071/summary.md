# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.34

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.19
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.725 | 1.317 | 17.254 |
| call_untrusted | 15.335 | 15.604 | 24.851 |
| reconstruct_response | 16.154 | 15.777 | 27.442 |
| **Total** | **35.214** | **33.873** | **55.916** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 11 |
