# Evaluation Summary

Total cases: 150

## Composite Score
- average: 68.00

## Score Breakdown
- exact_match: 68.00
- f1: 73.31

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.065 | 0.002 | 0.063 |
| summarize_hop1 | 2.410 | 2.180 | 4.019 |
| query_hop2 | 1.265 | 1.252 | 1.716 |
| retrieve_hop2 | 0.493 | 0.002 | 1.679 |
| summarize_hop2 | 2.202 | 2.123 | 3.191 |
| answer | 0.941 | 0.881 | 1.415 |
| **Total** | **7.375** | **6.948** | **11.640** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 48 |
