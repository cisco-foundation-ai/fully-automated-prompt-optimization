# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.91

## Score Breakdown
- leakage_fraction: 0.07
- privacy: 93.43
- quality: 96.40
- quality_passed: 0.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.321 | 1.213 | 9.037 |
| call_untrusted | 4.283 | 2.283 | 15.724 |
| reconstruct_response | 3.333 | 1.819 | 13.093 |
| **Total** | **9.937** | **5.777** | **31.022** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 17 |
