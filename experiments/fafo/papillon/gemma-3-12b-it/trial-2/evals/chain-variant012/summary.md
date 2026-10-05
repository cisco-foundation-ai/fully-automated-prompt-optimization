# Evaluation Summary

Total cases: 111

## Composite Score
- average: 93.02

## Score Breakdown
- leakage_fraction: 0.08
- privacy: 92.35
- quality: 93.69
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 6.914 | 1.752 | 20.506 |
| call_untrusted | 12.510 | 12.046 | 22.059 |
| reconstruct_response | 12.535 | 11.611 | 21.797 |
| **Total** | **31.960** | **27.155** | **55.423** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 17 |
