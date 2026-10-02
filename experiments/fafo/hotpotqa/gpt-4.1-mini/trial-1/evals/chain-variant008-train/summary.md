# Evaluation Summary

Total cases: 150

## Composite Score
- average: 72.00

## Score Breakdown
- exact_match: 72.00
- f1: 77.25

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.027 | 0.002 | 0.029 |
| summarize_hop1 | 3.634 | 3.085 | 6.880 |
| query_hop2 | 2.086 | 1.831 | 3.720 |
| retrieve_hop2 | 0.697 | 0.037 | 1.712 |
| summarize_hop2 | 3.083 | 2.847 | 4.718 |
| answer | 1.776 | 1.505 | 3.401 |
| **Total** | **11.303** | **10.524** | **18.817** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 42 |
