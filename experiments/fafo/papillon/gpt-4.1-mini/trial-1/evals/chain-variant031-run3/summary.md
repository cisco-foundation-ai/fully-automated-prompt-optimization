# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.24

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 95.68
- quality: 92.79
- quality_passed: 0.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.733 | 2.340 | 25.450 |
| call_untrusted | 6.665 | 3.759 | 20.427 |
| reconstruct_response | 6.025 | 3.810 | 16.084 |
| **Total** | **18.423** | **10.927** | **56.258** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 15 |
