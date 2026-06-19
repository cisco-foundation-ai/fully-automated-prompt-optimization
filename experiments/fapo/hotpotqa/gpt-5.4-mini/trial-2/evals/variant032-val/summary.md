# Evaluation Summary

Total cases: 300

## Composite Score
- average: 71.00

## Score Breakdown
- exact_match: 71.00
- f1: 78.30

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.037 | 0.002 | 0.008 |
| summarize_hop1 | 2.342 | 2.233 | 3.397 |
| query_hop2 | 1.335 | 1.168 | 1.798 |
| retrieve_hop2 | 0.303 | 0.002 | 1.590 |
| summarize_hop2 | 1.676 | 1.563 | 2.379 |
| answer | 0.863 | 0.827 | 1.251 |
| **Total** | **6.556** | **6.104** | **9.056** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 87 |
