# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.75

## Score Breakdown
- leakage_fraction: 0.06
- privacy: 94.20
- quality: 97.30
- quality_passed: 0.97

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.500 | 2.406 | 23.928 |
| call_untrusted | 7.332 | 3.700 | 25.129 |
| reconstruct_response | 8.395 | 4.761 | 27.886 |
| **Total** | **21.227** | **11.866** | **71.583** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 14 |
