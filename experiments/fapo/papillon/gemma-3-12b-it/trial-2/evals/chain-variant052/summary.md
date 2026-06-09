# Evaluation Summary

Total cases: 111

## Composite Score
- average: 94.29

## Score Breakdown
- leakage_fraction: 0.07
- privacy: 93.08
- quality: 95.50
- quality_passed: 0.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 5.271 | 1.618 | 32.457 |
| call_untrusted | 16.187 | 13.387 | 34.556 |
| reconstruct_response | 15.976 | 13.346 | 37.530 |
| **Total** | **37.433** | **31.283** | **80.265** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 17 |
