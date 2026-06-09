# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.34

## Score Breakdown
- leakage_fraction: 0.06
- privacy: 94.49
- quality: 98.20
- quality_passed: 0.98

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.610 | 1.202 | 15.817 |
| call_untrusted | 11.547 | 10.912 | 20.580 |
| reconstruct_response | 13.013 | 13.156 | 24.172 |
| **Total** | **28.170** | **26.202** | **55.156** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 11 |
