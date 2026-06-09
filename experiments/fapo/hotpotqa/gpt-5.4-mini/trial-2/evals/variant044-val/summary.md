# Evaluation Summary

Total cases: 300

## Composite Score
- average: 68.00

## Score Breakdown
- exact_match: 68.00
- f1: 76.14

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.031 | 0.002 | 0.010 |
| summarize_hop1 | 2.444 | 2.198 | 3.668 |
| query_hop2 | 1.401 | 1.139 | 2.277 |
| retrieve_hop2 | 0.337 | 0.003 | 1.595 |
| summarize_hop2 | 1.766 | 1.583 | 2.552 |
| answer | 1.059 | 0.881 | 1.693 |
| **Total** | **7.038** | **6.271** | **11.293** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 96 |
