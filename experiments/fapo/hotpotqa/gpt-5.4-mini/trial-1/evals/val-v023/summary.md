# Evaluation Summary

Total cases: 300

## Composite Score
- average: 71.00

## Score Breakdown
- exact_match: 71.00
- f1: 78.61

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.142 | 0.002 | 0.120 |
| summarize_hop1 | 1.277 | 1.208 | 1.853 |
| query_hop2 | 1.116 | 1.000 | 1.712 |
| retrieve_hop2 | 0.391 | 0.002 | 1.578 |
| summarize_hop2 | 1.519 | 1.426 | 2.252 |
| answer | 0.805 | 0.766 | 1.198 |
| **Total** | **5.250** | **4.723** | **7.767** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 86 |
| query_hop2 | 1 |
