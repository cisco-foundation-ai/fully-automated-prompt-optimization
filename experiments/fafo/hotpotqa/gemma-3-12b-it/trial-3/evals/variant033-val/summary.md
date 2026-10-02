# Evaluation Summary

Total cases: 300

## Composite Score
- average: 57.00

## Score Breakdown
- exact_match: 57.00
- f1: 67.56

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.028 | 0.002 | 0.011 |
| summarize_hop1 | 2.070 | 1.837 | 3.683 |
| query_hop2 | 1.094 | 1.019 | 1.809 |
| retrieve_hop2 | 0.503 | 0.002 | 1.577 |
| summarize_hop2 | 3.797 | 3.641 | 6.916 |
| answer | 1.161 | 1.030 | 2.073 |
| **Total** | **8.653** | **8.305** | **13.119** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 129 |
