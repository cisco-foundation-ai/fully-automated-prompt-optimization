# Evaluation Summary

Total cases: 300

## Composite Score
- average: 67.33

## Score Breakdown
- exact_match: 67.33
- f1: 74.56

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.094 | 1.140 | 1.691 |
| summarize_hop1 | 3.486 | 2.899 | 6.692 |
| query_hop2 | 2.040 | 1.805 | 3.648 |
| retrieve_hop2 | 1.339 | 1.337 | 1.618 |
| summarize_hop2 | 3.206 | 2.966 | 4.909 |
| answer | 1.676 | 1.563 | 2.688 |
| **Total** | **12.841** | **12.101** | **18.600** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 98 |
