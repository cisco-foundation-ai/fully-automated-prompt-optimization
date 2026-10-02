# Evaluation Summary

Total cases: 221

## Composite Score
- average: 89.75

## Score Breakdown
- leakage_fraction: 0.20
- privacy: 80.40
- quality: 99.10
- quality_passed: 0.99

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.202 | 1.939 | 9.577 |
| call_untrusted | 4.451 | 2.496 | 15.596 |
| reconstruct_response | 4.074 | 2.372 | 12.935 |
| **Total** | **11.726** | **8.078** | **34.324** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 58 |
