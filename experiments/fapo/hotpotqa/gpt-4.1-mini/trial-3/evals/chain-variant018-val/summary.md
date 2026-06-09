# Evaluation Summary

Total cases: 300

## Composite Score
- average: 65.00

## Score Breakdown
- exact_match: 65.00
- f1: 72.10

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.003 |
| summarize_hop1 | 3.887 | 3.381 | 7.173 |
| query_hop2 | 2.145 | 1.942 | 3.584 |
| retrieve_hop2 | 0.731 | 0.264 | 1.667 |
| summarize_hop2 | 4.100 | 3.642 | 7.297 |
| answer | 1.660 | 1.442 | 2.782 |
| **Total** | **12.525** | **11.348** | **20.623** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 105 |
