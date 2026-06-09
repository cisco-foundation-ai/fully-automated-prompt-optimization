# Evaluation Summary

Total cases: 300

## Composite Score
- average: 68.00

## Score Breakdown
- exact_match: 68.00
- f1: 76.07

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.064 | 1.274 | 1.658 |
| summarize_hop1 | 1.386 | 1.159 | 2.075 |
| query_hop2 | 1.280 | 1.119 | 1.724 |
| retrieve_hop2 | 1.305 | 1.308 | 1.611 |
| summarize_hop2 | 1.637 | 1.498 | 2.345 |
| answer | 1.122 | 0.839 | 1.792 |
| **Total** | **7.794** | **7.127** | **11.654** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 96 |
