# Evaluation Summary

Total cases: 300

## Composite Score
- average: 68.67

## Score Breakdown
- exact_match: 68.67
- f1: 75.95

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.027 | 0.002 | 0.010 |
| summarize_hop1 | 4.111 | 3.538 | 8.524 |
| query_hop2 | 2.210 | 1.869 | 4.502 |
| retrieve_hop2 | 0.325 | 0.002 | 1.304 |
| summarize_hop2 | 3.628 | 3.162 | 6.949 |
| answer | 2.129 | 1.823 | 3.462 |
| **Total** | **12.431** | **11.468** | **19.422** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 93 |
| query_hop2 | 1 |
