# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.67

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 95.65
- quality: 93.69
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 2.331 | 1.105 | 8.337 |
| call_untrusted | 3.272 | 1.864 | 10.865 |
| reconstruct_response | 2.290 | 1.413 | 7.637 |
| **Total** | **7.892** | **4.922** | **25.891** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 13 |
