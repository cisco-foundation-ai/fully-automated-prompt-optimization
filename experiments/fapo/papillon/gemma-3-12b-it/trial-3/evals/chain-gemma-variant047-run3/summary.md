# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.53

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 95.77
- quality: 97.30
- quality_passed: 0.97

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.650 | 1.325 | 17.898 |
| call_untrusted | 11.269 | 11.210 | 22.456 |
| reconstruct_response | 11.173 | 10.696 | 23.340 |
| **Total** | **26.092** | **25.564** | **51.277** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 11 |
