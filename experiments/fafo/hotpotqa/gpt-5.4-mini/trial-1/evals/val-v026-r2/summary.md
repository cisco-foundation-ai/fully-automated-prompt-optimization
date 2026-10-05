# Evaluation Summary

Total cases: 300

## Composite Score
- average: 68.67

## Score Breakdown
- exact_match: 68.67
- f1: 76.19

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.147 | 0.002 | 0.107 |
| summarize_hop1 | 1.249 | 1.141 | 1.765 |
| query_hop2 | 1.119 | 1.022 | 1.663 |
| retrieve_hop2 | 0.489 | 0.002 | 1.645 |
| summarize_hop2 | 1.493 | 1.414 | 2.097 |
| answer | 0.784 | 0.698 | 1.173 |
| **Total** | **5.282** | **4.639** | **9.468** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 93 |
| query_hop2 | 1 |
