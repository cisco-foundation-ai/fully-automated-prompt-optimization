# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.72

## Score Breakdown
- leakage_fraction: 0.01
- privacy: 98.65
- quality: 92.79
- quality_passed: 0.93

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 1.692 | 1.046 | 4.777 |
| call_untrusted | 2.696 | 1.580 | 9.164 |
| reconstruct_response | 1.855 | 1.294 | 5.366 |
| **Total** | **6.243** | **4.271** | **19.844** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 10 |
