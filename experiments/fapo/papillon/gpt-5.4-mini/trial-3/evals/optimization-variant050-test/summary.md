# Evaluation Summary

Total cases: 442

## Composite Score
- average: 96.42

## Score Breakdown
- leakage_fraction: 0.01
- privacy: 98.94
- quality: 93.89
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 1.777 | 1.017 | 5.977 |
| call_untrusted | 2.823 | 1.592 | 9.692 |
| reconstruct_response | 1.946 | 1.236 | 6.393 |
| **Total** | **6.546** | **4.197** | **20.545** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 33 |
| redact_query | 1 |
