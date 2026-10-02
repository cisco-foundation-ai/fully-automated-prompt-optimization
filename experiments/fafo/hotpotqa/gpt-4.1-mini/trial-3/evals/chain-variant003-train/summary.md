# Evaluation Summary

Total cases: 150

## Composite Score
- average: 74.00

## Score Breakdown
- exact_match: 74.00
- f1: 79.32

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.004 | 0.002 | 0.007 |
| summarize_hop1 | 2.995 | 2.695 | 4.991 |
| query_hop2 | 1.653 | 1.554 | 2.684 |
| retrieve_hop2 | 1.702 | 1.612 | 1.745 |
| summarize_hop2 | 2.701 | 2.399 | 4.308 |
| answer | 1.202 | 1.149 | 1.604 |
| **Total** | **10.255** | **9.608** | **15.696** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 39 |
