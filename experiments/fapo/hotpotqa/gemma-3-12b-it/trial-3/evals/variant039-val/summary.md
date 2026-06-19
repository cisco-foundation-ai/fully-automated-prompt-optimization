# Evaluation Summary

Total cases: 300

## Composite Score
- average: 56.00

## Score Breakdown
- exact_match: 56.00
- f1: 67.29

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.039 | 0.002 | 0.013 |
| summarize_hop1 | 2.302 | 2.133 | 3.919 |
| query_hop2 | 1.057 | 1.007 | 1.492 |
| retrieve_hop2 | 0.444 | 0.002 | 1.611 |
| summarize_hop2 | 3.288 | 3.031 | 5.413 |
| answer | 1.116 | 1.048 | 1.718 |
| **Total** | **8.246** | **7.832** | **12.634** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 132 |
