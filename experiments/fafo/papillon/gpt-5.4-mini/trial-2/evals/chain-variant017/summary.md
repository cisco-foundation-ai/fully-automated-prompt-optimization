# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.77

## Score Breakdown
- leakage_fraction: 0.06
- privacy: 94.44
- quality: 99.10
- quality_passed: 0.99

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.367 | 1.172 | 8.599 |
| call_untrusted | 4.167 | 2.275 | 16.065 |
| reconstruct_response | 3.030 | 1.657 | 11.312 |
| **Total** | **9.564** | **5.468** | **31.687** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 11 |
