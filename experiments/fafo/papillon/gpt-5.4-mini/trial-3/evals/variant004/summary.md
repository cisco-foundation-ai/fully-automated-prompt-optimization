# Evaluation Summary

Total cases: 111

## Composite Score
- average: 98.05

## Score Breakdown
- leakage_fraction: 0.00
- privacy: 99.70
- quality: 96.40
- quality_passed: 0.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 1.551 | 1.043 | 4.686 |
| call_untrusted | 3.207 | 1.766 | 12.407 |
| reconstruct_response | 2.398 | 1.410 | 8.850 |
| **Total** | **7.156** | **4.568** | **22.402** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 5 |
