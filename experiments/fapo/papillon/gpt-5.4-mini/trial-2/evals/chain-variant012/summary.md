# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.11

## Score Breakdown
- leakage_fraction: 0.07
- privacy: 92.92
- quality: 97.30
- quality_passed: 0.97

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.206 | 1.200 | 8.170 |
| call_untrusted | 4.361 | 2.249 | 16.562 |
| reconstruct_response | 3.099 | 1.627 | 12.121 |
| **Total** | **9.665** | **5.467** | **30.962** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 16 |
