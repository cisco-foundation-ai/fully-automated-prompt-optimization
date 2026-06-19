# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.47

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.45
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 1.814 | 1.062 | 5.565 |
| call_untrusted | 2.743 | 1.826 | 7.189 |
| reconstruct_response | 2.040 | 1.394 | 6.425 |
| **Total** | **6.598** | **4.444** | **19.638** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 9 |
