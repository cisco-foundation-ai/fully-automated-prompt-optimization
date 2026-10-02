# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.89

## Score Breakdown
- leakage_fraction: 0.08
- privacy: 91.59
- quality: 98.20
- quality_passed: 0.98

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 1.964 | 1.204 | 5.772 |
| call_untrusted | 3.917 | 2.171 | 14.858 |
| reconstruct_response | 2.906 | 1.775 | 8.861 |
| **Total** | **8.787** | **5.667** | **25.877** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 14 |
