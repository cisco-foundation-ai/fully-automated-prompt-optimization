# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.55

## Score Breakdown
- leakage_fraction: 0.02
- privacy: 98.50
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.329 | 1.159 | 9.314 |
| call_untrusted | 4.060 | 2.064 | 15.774 |
| reconstruct_response | 2.932 | 1.497 | 9.465 |
| **Total** | **9.321** | **4.786** | **25.989** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 9 |
