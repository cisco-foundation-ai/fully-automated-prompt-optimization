# Evaluation Summary

Total cases: 300

## Composite Score
- average: 63.00

## Score Breakdown
- exact_match: 63.00
- f1: 71.15

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.033 | 0.002 | 0.011 |
| summarize_hop1 | 2.389 | 2.157 | 4.175 |
| query_hop2 | 1.133 | 1.034 | 1.571 |
| retrieve_hop2 | 0.530 | 0.002 | 1.596 |
| summarize_hop2 | 2.679 | 2.615 | 4.194 |
| answer | 1.123 | 1.031 | 1.639 |
| **Total** | **7.887** | **7.480** | **11.721** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 111 |
