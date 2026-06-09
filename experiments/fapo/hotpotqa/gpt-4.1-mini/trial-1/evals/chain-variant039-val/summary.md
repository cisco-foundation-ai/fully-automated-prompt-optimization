# Evaluation Summary

Total cases: 300

## Composite Score
- average: 70.00

## Score Breakdown
- exact_match: 70.00
- f1: 76.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.022 | 0.002 | 0.009 |
| summarize_hop1 | 4.341 | 3.556 | 8.697 |
| query_hop2 | 2.101 | 1.789 | 3.422 |
| retrieve_hop2 | 0.276 | 0.002 | 1.576 |
| summarize_hop2 | 3.570 | 3.089 | 5.901 |
| answer | 2.034 | 1.796 | 3.203 |
| **Total** | **12.344** | **11.038** | **19.994** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 90 |
