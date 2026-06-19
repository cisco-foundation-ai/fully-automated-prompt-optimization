# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.74

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 95.78
- quality: 93.69
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 6.507 | 2.466 | 28.247 |
| call_untrusted | 8.275 | 4.670 | 25.817 |
| reconstruct_response | 9.002 | 5.392 | 30.513 |
| **Total** | **23.784** | **16.179** | **71.564** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 14 |
