# Evaluation Summary

Total cases: 442

## Composite Score
- average: 96.98

## Score Breakdown
- leakage_fraction: 0.02
- privacy: 98.48
- quality: 95.48
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.229 | 1.166 | 7.644 |
| call_untrusted | 3.524 | 2.114 | 11.545 |
| reconstruct_response | 2.505 | 1.524 | 7.752 |
| **Total** | **8.258** | **5.446** | **23.401** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 27 |
