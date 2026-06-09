# Evaluation Summary

Total cases: 111

## Composite Score
- average: 93.24

## Score Breakdown
- leakage_fraction: 0.05
- privacy: 94.59
- quality: 91.89
- quality_passed: 0.92

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.410 | 1.073 | 8.897 |
| call_untrusted | 3.475 | 1.904 | 11.138 |
| reconstruct_response | 2.677 | 1.528 | 8.415 |
| **Total** | **8.562** | **5.013** | **25.045** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 19 |
