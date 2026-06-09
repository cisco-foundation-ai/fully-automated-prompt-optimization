# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.69

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 95.88
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.558 | 1.261 | 18.330 |
| call_untrusted | 11.858 | 12.047 | 22.016 |
| reconstruct_response | 11.840 | 11.409 | 21.180 |
| **Total** | **27.255** | **27.359** | **52.389** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 13 |
