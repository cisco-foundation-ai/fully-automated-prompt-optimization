# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.09

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 96.49
- quality: 93.69
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.551 | 1.179 | 17.503 |
| call_untrusted | 11.341 | 11.365 | 20.420 |
| reconstruct_response | 11.092 | 11.142 | 21.239 |
| **Total** | **25.983** | **25.175** | **51.910** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 14 |
