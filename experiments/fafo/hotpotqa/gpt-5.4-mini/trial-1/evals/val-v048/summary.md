# Evaluation Summary

Total cases: 300

## Composite Score
- average: 68.00

## Score Breakdown
- exact_match: 68.00
- f1: 75.54

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.155 | 0.002 | 0.103 |
| summarize_hop1 | 1.352 | 1.248 | 2.065 |
| query_hop2 | 1.096 | 1.052 | 1.506 |
| retrieve_hop2 | 0.332 | 0.002 | 1.664 |
| summarize_hop2 | 1.647 | 1.539 | 2.477 |
| answer | 0.884 | 0.772 | 1.269 |
| **Total** | **5.467** | **4.823** | **9.018** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 96 |
