# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.28

## Score Breakdown
- leakage_fraction: 0.05
- privacy: 95.26
- quality: 97.30
- quality_passed: 0.97

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.334 | 1.161 | 8.147 |
| call_untrusted | 2.942 | 1.763 | 8.889 |
| reconstruct_response | 1.914 | 1.244 | 4.958 |
| **Total** | **7.189** | **4.555** | **20.143** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 12 |
