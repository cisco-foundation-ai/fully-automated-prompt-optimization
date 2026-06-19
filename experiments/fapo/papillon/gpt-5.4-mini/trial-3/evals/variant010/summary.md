# Evaluation Summary

Total cases: 111

## Composite Score
- average: 97.18

## Score Breakdown
- leakage_fraction: 0.01
- privacy: 98.86
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 1.886 | 1.130 | 6.191 |
| call_untrusted | 2.770 | 1.635 | 10.352 |
| reconstruct_response | 1.840 | 1.277 | 6.038 |
| **Total** | **6.496** | **4.962** | **18.352** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 9 |
