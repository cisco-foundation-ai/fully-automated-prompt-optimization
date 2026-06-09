# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.64

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.89
- quality: 96.40
- quality_passed: 0.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 1.937 | 1.187 | 6.777 |
| call_untrusted | 3.610 | 2.019 | 11.452 |
| reconstruct_response | 2.289 | 1.490 | 7.142 |
| **Total** | **7.836** | **5.338** | **23.676** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 10 |
