# Evaluation Summary

Total cases: 150

## Composite Score
- average: 66.00

## Score Breakdown
- exact_match: 66.00
- f1: 73.28

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.056 | 0.003 | 0.043 |
| summarize_hop1 | 2.464 | 2.220 | 4.451 |
| query_hop2 | 1.101 | 1.031 | 1.565 |
| retrieve_hop2 | 0.587 | 0.003 | 1.600 |
| summarize_hop2 | 3.796 | 2.616 | 3.901 |
| answer | 1.099 | 1.059 | 1.704 |
| **Total** | **9.102** | **7.527** | **12.278** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 51 |
