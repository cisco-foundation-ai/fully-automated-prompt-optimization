# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.72

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.85
- quality: 94.59
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 1.901 | 1.059 | 6.372 |
| call_untrusted | 3.340 | 1.916 | 9.720 |
| reconstruct_response | 2.549 | 1.469 | 7.384 |
| **Total** | **7.790** | **4.917** | **25.627** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 12 |
