# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.28

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 97.06
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 4.657 | 1.609 | 21.390 |
| call_untrusted | 7.074 | 2.968 | 27.677 |
| reconstruct_response | 5.556 | 2.806 | 20.166 |
| **Total** | **17.287** | **7.599** | **55.289** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 10 |
