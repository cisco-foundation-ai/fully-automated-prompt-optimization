# Evaluation Summary

Total cases: 300

## Composite Score
- average: 65.00

## Score Breakdown
- exact_match: 65.00
- f1: 72.63

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.027 | 0.002 | 0.006 |
| summarize_hop1 | 2.482 | 2.189 | 3.652 |
| query_hop2 | 1.328 | 1.079 | 2.619 |
| retrieve_hop2 | 0.643 | 0.007 | 1.570 |
| summarize_hop2 | 1.805 | 1.618 | 2.837 |
| answer | 1.030 | 0.853 | 1.785 |
| **Total** | **7.314** | **6.701** | **10.889** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 105 |
