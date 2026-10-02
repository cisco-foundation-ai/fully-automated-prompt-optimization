# Evaluation Summary

Total cases: 300

## Composite Score
- average: 64.67

## Score Breakdown
- exact_match: 64.67
- f1: 73.09

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.131 | 0.002 | 0.115 |
| summarize_hop1 | 1.204 | 1.125 | 1.825 |
| query_hop2 | 1.104 | 1.014 | 1.519 |
| retrieve_hop2 | 0.435 | 0.002 | 1.649 |
| summarize_hop2 | 1.473 | 1.402 | 2.191 |
| answer | 0.767 | 0.707 | 1.157 |
| **Total** | **5.114** | **4.557** | **8.197** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 106 |
