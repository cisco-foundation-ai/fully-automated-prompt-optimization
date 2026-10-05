# Evaluation Summary

Total cases: 150

## Composite Score
- average: 48.67

## Score Breakdown
- exact_match: 48.67
- f1: 54.05

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.034 | 0.002 | 0.018 |
| summarize_hop1 | 1.174 | 1.070 | 2.108 |
| query_hop2 | 1.222 | 1.054 | 1.891 |
| retrieve_hop2 | 1.252 | 1.329 | 1.788 |
| summarize_hop2 | 1.098 | 1.054 | 1.642 |
| answer | 0.924 | 0.852 | 1.433 |
| **Total** | **5.705** | **5.357** | **7.876** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 77 |
