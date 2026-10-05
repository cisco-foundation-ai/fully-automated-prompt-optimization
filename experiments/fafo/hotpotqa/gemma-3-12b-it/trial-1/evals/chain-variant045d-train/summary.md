# Evaluation Summary

Total cases: 150

## Composite Score
- average: 66.00

## Score Breakdown
- exact_match: 66.00
- f1: 73.80

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.045 | 0.003 | 0.057 |
| summarize_hop1 | 2.373 | 2.203 | 4.192 |
| query_hop2 | 1.030 | 0.990 | 1.400 |
| retrieve_hop2 | 0.460 | 0.002 | 1.551 |
| summarize_hop2 | 2.574 | 2.434 | 4.009 |
| answer | 1.060 | 0.998 | 1.712 |
| **Total** | **7.542** | **7.293** | **11.558** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 51 |
