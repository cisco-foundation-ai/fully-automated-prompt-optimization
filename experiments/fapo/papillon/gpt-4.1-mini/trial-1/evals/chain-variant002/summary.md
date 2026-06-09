# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.30

## Score Breakdown
- leakage_fraction: 0.05
- privacy: 94.91
- quality: 93.69
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 6.404 | 2.245 | 28.041 |
| call_untrusted | 7.601 | 4.247 | 20.434 |
| reconstruct_response | 8.222 | 4.290 | 30.760 |
| **Total** | **22.227** | **12.426** | **80.683** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 16 |
