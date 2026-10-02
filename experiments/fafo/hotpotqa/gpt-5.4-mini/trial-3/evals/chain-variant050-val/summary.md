# Evaluation Summary

Total cases: 300

## Composite Score
- average: 71.67

## Score Breakdown
- exact_match: 71.67
- f1: 77.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.034 | 0.002 | 0.008 |
| summarize_hop1 | 1.327 | 1.227 | 1.992 |
| query_hop2 | 1.149 | 1.014 | 1.965 |
| retrieve_hop2 | 0.299 | 0.002 | 1.559 |
| summarize_hop2 | 1.445 | 1.236 | 1.857 |
| answer | 1.128 | 0.907 | 1.582 |
| **Total** | **5.381** | **4.694** | **8.809** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 84 |
| query_hop2 | 1 |
