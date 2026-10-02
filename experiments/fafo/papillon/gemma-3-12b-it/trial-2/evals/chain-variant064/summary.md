# Evaluation Summary

Total cases: 111

## Composite Score
- average: 93.97

## Score Breakdown
- leakage_fraction: 0.05
- privacy: 95.15
- quality: 92.79
- quality_passed: 0.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.224 | 1.178 | 18.927 |
| call_untrusted | 12.758 | 11.247 | 26.890 |
| reconstruct_response | 12.933 | 11.836 | 26.968 |
| **Total** | **30.915** | **25.472** | **65.604** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 18 |
