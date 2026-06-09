# Evaluation Summary

Total cases: 150

## Composite Score
- average: 74.67

## Score Breakdown
- exact_match: 74.67
- f1: 81.74

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.026 | 0.002 | 0.011 |
| summarize_hop1 | 1.872 | 1.510 | 2.324 |
| query_hop2 | 1.510 | 1.075 | 2.588 |
| retrieve_hop2 | 1.047 | 1.054 | 1.698 |
| summarize_hop2 | 1.674 | 1.271 | 2.617 |
| answer | 1.021 | 0.881 | 1.186 |
| **Total** | **7.149** | **5.839** | **19.706** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 38 |
