# Evaluation Summary

Total cases: 150

## Composite Score
- average: 71.33

## Score Breakdown
- exact_match: 71.33
- f1: 78.41

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.027 | 0.002 | 0.016 |
| summarize_hop1 | 4.720 | 3.534 | 10.819 |
| query_hop2 | 1.818 | 1.589 | 2.460 |
| retrieve_hop2 | 0.726 | 0.085 | 1.698 |
| summarize_hop2 | 2.400 | 2.192 | 3.763 |
| answer | 1.215 | 1.129 | 1.880 |
| **Total** | **10.907** | **9.290** | **19.307** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 43 |
