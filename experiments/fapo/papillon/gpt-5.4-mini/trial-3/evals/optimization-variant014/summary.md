# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.32

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.15
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 1.743 | 1.159 | 5.570 |
| call_untrusted | 3.044 | 1.655 | 10.168 |
| reconstruct_response | 2.240 | 1.437 | 6.849 |
| **Total** | **7.026** | **4.470** | **19.481** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 10 |
