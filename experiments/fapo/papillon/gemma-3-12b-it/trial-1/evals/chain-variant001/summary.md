# Evaluation Summary

Total cases: 111

## Composite Score
- average: 67.33

## Score Breakdown
- leakage_fraction: 0.64
- privacy: 36.46
- quality: 98.20
- quality_passed: 0.98

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 7.672 | 5.105 | 22.664 |
| call_untrusted | 5.549 | 5.149 | 13.212 |
| reconstruct_response | 9.177 | 8.783 | 19.639 |
| **Total** | **22.397** | **19.813** | **49.431** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 82 |
