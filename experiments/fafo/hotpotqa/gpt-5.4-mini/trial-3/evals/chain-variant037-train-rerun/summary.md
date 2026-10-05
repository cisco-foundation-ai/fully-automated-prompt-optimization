# Evaluation Summary

Total cases: 150

## Composite Score
- average: 74.67

## Score Breakdown
- exact_match: 74.67
- f1: 81.92

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.081 | 0.002 | 0.060 |
| summarize_hop1 | 1.333 | 1.266 | 1.919 |
| query_hop2 | 1.102 | 0.992 | 1.629 |
| retrieve_hop2 | 0.587 | 0.002 | 1.663 |
| summarize_hop2 | 1.421 | 1.247 | 2.003 |
| answer | 0.996 | 0.943 | 1.373 |
| **Total** | **5.519** | **4.816** | **8.487** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 38 |
