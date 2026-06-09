# Evaluation Summary

Total cases: 150

## Composite Score
- average: 72.67

## Score Breakdown
- exact_match: 72.67
- f1: 78.07

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.095 | 0.002 | 0.140 |
| summarize_hop1 | 2.050 | 1.946 | 2.976 |
| query_hop2 | 1.133 | 1.019 | 1.405 |
| retrieve_hop2 | 0.533 | 0.002 | 1.648 |
| summarize_hop2 | 1.745 | 1.641 | 2.464 |
| answer | 0.851 | 0.817 | 1.309 |
| **Total** | **6.408** | **5.845** | **9.408** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 41 |
