# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.94

## Score Breakdown
- leakage_fraction: 0.05
- privacy: 94.58
- quality: 97.30
- quality_passed: 0.97

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.536 | 1.931 | 23.911 |
| call_untrusted | 19.163 | 18.083 | 37.742 |
| reconstruct_response | 20.286 | 17.271 | 42.459 |
| **Total** | **44.984** | **44.719** | **89.757** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 14 |
