# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.44

## Score Breakdown
- leakage_fraction: 0.05
- privacy: 95.20
- quality: 93.69
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 1.815 | 1.073 | 6.288 |
| call_untrusted | 3.754 | 1.862 | 12.472 |
| reconstruct_response | 2.450 | 1.466 | 7.605 |
| **Total** | **8.018** | **4.568** | **22.708** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 15 |
