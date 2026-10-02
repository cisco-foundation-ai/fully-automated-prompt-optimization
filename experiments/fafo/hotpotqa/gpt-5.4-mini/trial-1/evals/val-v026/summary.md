# Evaluation Summary

Total cases: 300

## Composite Score
- average: 71.33

## Score Breakdown
- exact_match: 71.33
- f1: 78.04

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.103 | 0.002 | 0.112 |
| summarize_hop1 | 1.191 | 1.111 | 1.874 |
| query_hop2 | 1.106 | 1.020 | 1.607 |
| retrieve_hop2 | 0.525 | 0.002 | 1.649 |
| summarize_hop2 | 1.551 | 1.437 | 2.273 |
| answer | 0.802 | 0.742 | 1.154 |
| **Total** | **5.279** | **4.663** | **9.077** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 86 |
