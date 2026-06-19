# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.55

## Score Breakdown
- leakage_fraction: 0.05
- privacy: 94.89
- quality: 98.20
- quality_passed: 0.98

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 1.872 | 1.083 | 5.015 |
| call_untrusted | 3.443 | 1.772 | 12.693 |
| reconstruct_response | 2.319 | 1.341 | 7.040 |
| **Total** | **7.633** | **4.334** | **23.102** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 11 |
