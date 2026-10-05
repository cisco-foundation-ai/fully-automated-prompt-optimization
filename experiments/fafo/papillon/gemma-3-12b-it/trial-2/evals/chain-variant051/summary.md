# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.65

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 95.80
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.495 | 1.596 | 21.604 |
| call_untrusted | 17.461 | 14.399 | 37.240 |
| reconstruct_response | 17.564 | 15.256 | 35.384 |
| **Total** | **40.520** | **36.763** | **81.761** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 12 |
