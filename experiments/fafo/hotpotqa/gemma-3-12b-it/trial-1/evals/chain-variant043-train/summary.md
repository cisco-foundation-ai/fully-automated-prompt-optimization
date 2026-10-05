# Evaluation Summary

Total cases: 150

## Composite Score
- average: 68.00

## Score Breakdown
- exact_match: 68.00
- f1: 73.74

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.059 | 0.003 | 0.037 |
| summarize_hop1 | 2.545 | 2.335 | 5.271 |
| query_hop2 | 1.108 | 1.038 | 1.793 |
| retrieve_hop2 | 0.328 | 0.007 | 1.099 |
| summarize_hop2 | 2.713 | 2.514 | 4.276 |
| answer | 1.104 | 1.030 | 1.704 |
| **Total** | **7.857** | **7.503** | **11.347** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 48 |
