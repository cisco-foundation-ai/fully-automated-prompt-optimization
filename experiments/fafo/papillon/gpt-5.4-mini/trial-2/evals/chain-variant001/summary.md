# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.07

## Score Breakdown
- leakage_fraction: 0.06
- privacy: 94.44
- quality: 93.69
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.482 | 1.157 | 8.866 |
| call_untrusted | 4.040 | 2.176 | 15.135 |
| reconstruct_response | 2.968 | 1.692 | 10.747 |
| **Total** | **9.490** | **5.822** | **26.150** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 16 |
