# Evaluation Summary

Total cases: 111

## Composite Score
- average: 93.90

## Score Breakdown
- leakage_fraction: 0.06
- privacy: 94.11
- quality: 93.69
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 4.485 | 1.289 | 15.980 |
| call_untrusted | 3.780 | 2.169 | 13.142 |
| reconstruct_response | 3.189 | 1.943 | 8.424 |
| **Total** | **11.454** | **6.203** | **31.912** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 18 |
