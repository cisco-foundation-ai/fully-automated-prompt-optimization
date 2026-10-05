# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.54

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 95.78
- quality: 97.30
- quality_passed: 0.97

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.583 | 1.323 | 17.577 |
| call_untrusted | 11.650 | 12.236 | 21.490 |
| reconstruct_response | 12.543 | 11.566 | 24.651 |
| **Total** | **27.776** | **26.867** | **52.038** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 11 |
