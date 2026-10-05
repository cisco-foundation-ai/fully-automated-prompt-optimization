# Evaluation Summary

Total cases: 111

## Composite Score
- average: 90.87

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.06
- quality: 84.68
- quality_passed: 0.85

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.926 | 1.623 | 17.618 |
| call_untrusted | 6.986 | 3.501 | 29.348 |
| reconstruct_response | 5.876 | 2.813 | 18.261 |
| **Total** | **16.787** | **9.129** | **53.360** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 22 |
