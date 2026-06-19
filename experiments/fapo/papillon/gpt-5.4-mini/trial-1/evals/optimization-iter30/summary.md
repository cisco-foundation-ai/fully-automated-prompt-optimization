# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.07

## Score Breakdown
- leakage_fraction: 0.06
- privacy: 93.73
- quality: 96.40
- quality_passed: 0.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.017 | 1.153 | 5.956 |
| call_untrusted | 3.933 | 2.058 | 13.968 |
| reconstruct_response | 2.981 | 1.704 | 9.290 |
| **Total** | **8.931** | **5.703** | **26.567** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 15 |
