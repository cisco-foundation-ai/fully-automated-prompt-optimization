# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.31

## Score Breakdown
- leakage_fraction: 0.05
- privacy: 94.94
- quality: 93.69
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.362 | 1.247 | 8.415 |
| call_untrusted | 4.972 | 2.466 | 17.810 |
| reconstruct_response | 3.590 | 1.788 | 15.307 |
| **Total** | **10.924** | **6.689** | **37.708** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 18 |
