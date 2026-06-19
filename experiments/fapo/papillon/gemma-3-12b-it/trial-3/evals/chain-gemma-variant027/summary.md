# Evaluation Summary

Total cases: 111

## Composite Score
- average: 96.39

## Score Breakdown
- leakage_fraction: 0.04
- privacy: 96.39
- quality: 96.40
- quality_passed: 0.96

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| redact_query | 3.653 | 1.281 | 18.482 |
| call_untrusted | 12.022 | 11.416 | 21.569 |
| reconstruct_response | 11.874 | 11.325 | 21.642 |
| **Total** | **27.549** | **25.707** | **58.433** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| reconstruct_response | 11 |
