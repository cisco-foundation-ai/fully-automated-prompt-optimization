# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.32

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 96.25
- quality: 96.40
- quality_passed: 0.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 1.807 | 1.048 | 6.233 |
| call_untrusted | 2.970 | 1.756 | 10.193 |
| reconstruct_response | 2.301 | 1.410 | 6.237 |
| **Total** | **7.078** | **4.456** | **21.006** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 10 |
