# Evaluation Summary

Total cases: 111

## Composite Score
- average: 97.60

## Score Breakdown
- leakage_fraction: 0.02
- privacy: 97.90
- quality: 97.30
- quality_passed: 0.97

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 1.974 | 1.128 | 6.548 |
| call_untrusted | 3.305 | 1.807 | 11.577 |
| reconstruct_response | 2.665 | 1.580 | 7.387 |
| **Total** | **7.944** | **5.164** | **19.696** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 7 |
