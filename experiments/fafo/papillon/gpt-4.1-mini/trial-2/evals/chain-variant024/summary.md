# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.57

## Score Breakdown
- leakage_fraction: 0.07
- privacy: 92.74
- quality: 96.40
- quality_passed: 0.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 7.370 | 2.439 | 41.109 |
| call_untrusted | 7.183 | 3.740 | 22.901 |
| reconstruct_response | 7.293 | 4.520 | 25.524 |
| **Total** | **21.845** | **14.112** | **81.436** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 17 |
