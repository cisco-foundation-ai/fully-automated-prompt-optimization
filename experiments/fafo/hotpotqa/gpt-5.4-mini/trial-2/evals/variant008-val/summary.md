# Evaluation Summary

Total cases: 300

## Composite Score
- average: 71.00

## Score Breakdown
- exact_match: 71.00
- f1: 78.18

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.029 | 0.002 | 0.009 |
| summarize_hop1 | 2.242 | 2.122 | 3.216 |
| query_hop2 | 1.158 | 1.084 | 1.664 |
| retrieve_hop2 | 0.839 | 0.100 | 1.653 |
| summarize_hop2 | 1.756 | 1.636 | 2.449 |
| answer | 0.888 | 0.826 | 1.394 |
| **Total** | **6.912** | **6.670** | **9.276** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 87 |
