# Evaluation Summary

Total cases: 111

## Composite Score
- average: 95.26

## Score Breakdown
- leakage_fraction: 0.03
- privacy: 96.82
- quality: 93.69
- quality_passed: 0.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.563 | 1.122 | 17.961 |
| call_untrusted | 11.591 | 11.605 | 20.298 |
| reconstruct_response | 12.122 | 11.825 | 22.795 |
| **Total** | **27.276** | **26.398** | **48.757** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 13 |
