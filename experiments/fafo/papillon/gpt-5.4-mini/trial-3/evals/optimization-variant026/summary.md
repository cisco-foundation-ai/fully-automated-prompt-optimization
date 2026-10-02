# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.98

## Score Breakdown
- leakage_fraction: 0.02
- privacy: 98.26
- quality: 93.69
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.227 | 1.176 | 8.683 |
| call_untrusted | 3.709 | 2.079 | 11.757 |
| reconstruct_response | 3.043 | 1.787 | 9.365 |
| **Total** | **8.979** | **5.839** | **23.234** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 11 |
