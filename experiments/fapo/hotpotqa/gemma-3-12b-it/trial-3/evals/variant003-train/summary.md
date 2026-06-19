# Evaluation Summary

Total cases: 150

## Composite Score
- average: 63.33

## Score Breakdown
- exact_match: 63.33
- f1: 70.72

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.022 | 0.002 | 0.017 |
| summarize_hop1 | 2.297 | 2.105 | 3.961 |
| query_hop2 | 0.977 | 0.958 | 1.318 |
| retrieve_hop2 | 1.216 | 1.086 | 1.700 |
| summarize_hop2 | 2.806 | 2.687 | 4.867 |
| answer | 1.152 | 1.060 | 1.659 |
| **Total** | **8.470** | **8.031** | **11.708** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 55 |
