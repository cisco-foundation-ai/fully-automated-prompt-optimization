# Evaluation Summary

Total cases: 300

## Composite Score
- average: 66.67

## Score Breakdown
- exact_match: 66.67
- f1: 75.01

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.155 | 0.002 | 0.125 |
| summarize_hop1 | 1.329 | 1.107 | 1.907 |
| query_hop2 | 1.082 | 1.018 | 1.505 |
| retrieve_hop2 | 0.415 | 0.002 | 1.613 |
| summarize_hop2 | 1.438 | 1.382 | 2.022 |
| answer | 0.848 | 0.746 | 1.300 |
| **Total** | **5.267** | **4.492** | **8.024** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 100 |
